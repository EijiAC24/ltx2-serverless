"""
Batch Generate: Generate multiple videos at once for cost efficiency
Uploads to FTP server for later posting
"""

import argparse
import base64
import os
from datetime import datetime, timezone
from pathlib import Path

# Load .env for local testing
from dotenv import load_dotenv
load_dotenv()

from accounts import get_account, list_accounts, DEFAULT_ACCOUNT
from config import DEFAULT_DURATION, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_STEPS
import grok_client
import sheets_client
import ltx_client
import ftp_client


def batch_generate(account_id: str = None, count: int = 5):
    """
    Batch generation flow:
    1. Generate N prompts with Grok (avoid past prompts)
    2. Generate N videos with Runpod (parallel jobs)
    3. Upload to FTP server
    4. Update Sheets
    """

    # Get account config
    account = get_account(account_id)
    account_id = account_id or DEFAULT_ACCOUNT
    print(f"\n{'='*60}")
    print(f"BATCH GENERATE: {count} videos")
    print(f"Account: {account['name']}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    # Override sheet name if specified
    if account.get("sheet_name"):
        os.environ["SHEET_NAME"] = account["sheet_name"]

    # --- Phase 1: Generate Prompts ---
    print(f"[1/{3}] Generating {count} prompts with Grok...")

    # Get past prompts from Sheets
    past_prompts = []
    try:
        all_rows = sheets_client.get_all_rows()
        past_prompts = [row["prompt"] for row in all_rows if row.get("prompt")]
        print(f"  Found {len(past_prompts)} past prompts to avoid")
    except Exception as e:
        print(f"  Warning: Could not fetch past prompts: {e}")

    try:
        prompts = grok_client.generate_prompts(
            count=count,
            style=account.get("style", "cinematic"),
            include_dialogue=True,
            theme=account.get("theme"),
            past_prompts=past_prompts,
        )

        if len(prompts) < count:
            print(f"  Warning: Only got {len(prompts)} prompts")

        for i, p in enumerate(prompts, 1):
            print(f"  [{i}] {p['caption']}")

    except Exception as e:
        print(f"  ERROR: {e}")
        return {"status": "error", "phase": "prompts", "error": str(e)}

    # --- Phase 2: Save to Sheets & Submit Jobs (warm-up strategy) ---
    print(f"\n[2/{3}] Submitting jobs to Runpod (warm-up strategy)...")

    jobs = []
    results = []
    total_cost = 0

    # First, save all prompts to sheets and prepare job data
    job_data = []
    for i, prompt_data in enumerate(prompts):
        try:
            sheets_client.add_prompts([prompt_data])
            rows = sheets_client.get_all_rows()
            row_id = rows[-1]["id"]
            job_data.append({"row_id": row_id, "prompt_data": prompt_data})
        except Exception as e:
            print(f"  [{i+1}] ERROR saving to sheets: {e}")

    if not job_data:
        return {"status": "error", "phase": "sheets", "error": "No prompts saved"}

    # Step 1: Submit first job to warm up worker
    print(f"\n  [Warm-up] Submitting first job to wake up worker...")
    first = job_data[0]
    try:
        job_id = ltx_client.submit_job(
            prompt=first["prompt_data"]["prompt"],
            duration=DEFAULT_DURATION,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            steps=DEFAULT_STEPS,
        )
        sheets_client.mark_generating(first["row_id"], job_id)
        print(f"  [Warm-up] Job {job_id[:20]}... submitted")
        print(f"  [Warm-up] Waiting for completion to warm up worker...")

        # Wait for first job to complete
        result = ltx_client.wait_for_completion(job_id)
        output = result.get("output", {})
        exec_time = result.get("executionTime", 0) / 1000
        cost = exec_time * 0.00106
        total_cost += cost
        print(f"  [Warm-up] Done in {exec_time:.1f}s (${cost:.4f}) - Worker is now warm!")

        # Process first video
        video_b64 = output.get("video_base64")
        if video_b64:
            video_bytes = base64.b64decode(video_b64)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{account_id}_{timestamp}_1.mp4"
            video_url = ftp_client.upload_video(video_bytes, filename)
            print(f"  [Warm-up] Uploaded: {filename}")
            sheets_client.mark_generated(
                first["row_id"],
                video_url=video_url,
                duration=output.get("duration", 10),
                resolution=output.get("resolution", "576x1024"),
                cost=cost,
            )
            results.append({
                "job_id": job_id,
                "filename": filename,
                "url": video_url,
                "cost": cost,
                "caption": first["prompt_data"]["caption"],
            })
    except Exception as e:
        print(f"  [Warm-up] ERROR: {e}")
        sheets_client.mark_error(first["row_id"], str(e))

    # Step 2: Submit remaining jobs in parallel (worker is warm now)
    remaining = job_data[1:]
    if remaining:
        print(f"\n  [Parallel] Submitting {len(remaining)} jobs to warm worker...")
        for i, data in enumerate(remaining):
            try:
                job_id = ltx_client.submit_job(
                    prompt=data["prompt_data"]["prompt"],
                    duration=DEFAULT_DURATION,
                    width=DEFAULT_WIDTH,
                    height=DEFAULT_HEIGHT,
                    steps=DEFAULT_STEPS,
                )
                sheets_client.mark_generating(data["row_id"], job_id)
                jobs.append({
                    "job_id": job_id,
                    "row_id": data["row_id"],
                    "prompt_data": data["prompt_data"],
                    "index": i + 2,  # 2, 3, 4, 5...
                })
                print(f"  [Parallel] Job {i+2}: {job_id[:20]}... submitted")
            except Exception as e:
                print(f"  [Parallel] Job {i+2} ERROR: {e}")

    # --- Phase 3: Wait for remaining jobs & Upload ---
    if jobs:
        print(f"\n[3/3] Waiting for {len(jobs)} remaining videos...")

        for job in jobs:
            job_id = job["job_id"]
            row_id = job["row_id"]
            prompt_data = job["prompt_data"]
            idx = job["index"]

            try:
                print(f"  [{idx}] Waiting for {job_id[:20]}...")
                result = ltx_client.wait_for_completion(job_id)

                output = result.get("output", {})
                exec_time = result.get("executionTime", 0) / 1000
                cost = exec_time * 0.00106
                total_cost += cost

                print(f"      Done in {exec_time:.1f}s (${cost:.4f})")

                # Get video bytes
                video_b64 = output.get("video_base64")
                if not video_b64:
                    raise Exception("No video in response")

                video_bytes = base64.b64decode(video_b64)

                # Generate filename
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"{account_id}_{timestamp}_{idx}.mp4"

                # Upload to FTP
                video_url = ftp_client.upload_video(video_bytes, filename)
                print(f"      Uploaded: {filename}")

                # Update sheets
                sheets_client.mark_generated(
                    row_id,
                    video_url=video_url,
                    duration=output.get("duration", 10),
                    resolution=output.get("resolution", "576x1024"),
                    cost=cost,
                )

                results.append({
                    "job_id": job_id,
                    "filename": filename,
                    "url": video_url,
                    "cost": cost,
                    "caption": prompt_data["caption"],
                })

            except Exception as e:
                print(f"      ERROR: {e}")
                sheets_client.mark_error(row_id, str(e))

    # --- Summary ---
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"  Videos generated: {len(results)}/{len(job_data)}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"{'='*60}\n")

    return {
        "status": "completed",
        "account": account_id,
        "videos_generated": len(results),
        "videos_requested": len(job_data),
        "total_cost": total_cost,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Batch video generation")
    parser.add_argument(
        "--account", "-a",
        default=DEFAULT_ACCOUNT,
        help=f"Account ID. Available: {list_accounts()}",
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=5,
        help="Number of videos to generate (default: 5)",
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List available accounts",
    )

    args = parser.parse_args()

    if args.list_accounts:
        print("Available accounts:")
        for acc_id in list_accounts():
            acc = get_account(acc_id)
            print(f"  - {acc_id}: {acc['name']}")
        return

    result = batch_generate(args.account, args.count)

    if result["status"] == "error":
        exit(1)


if __name__ == "__main__":
    main()
