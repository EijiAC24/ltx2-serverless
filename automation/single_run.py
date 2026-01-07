"""
Single Run: Generate 1 prompt → Create 1 video → Post immediately
Designed for multiple daily runs (e.g., 5x per day)
"""

import argparse
import random
import base64
import os
from datetime import datetime
from pathlib import Path

# Load .env for local testing
from dotenv import load_dotenv
load_dotenv()

from accounts import get_account, list_accounts, DEFAULT_ACCOUNT
from config import DEFAULT_DURATION, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_STEPS

# Output folder for generated videos
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
import grok_client
import sheets_client
import ltx_client

# Later client import (will fail gracefully if not configured)
try:
    import later_client
    LATER_AVAILABLE = True
except Exception:
    LATER_AVAILABLE = False


def run_single(account_id: str = None, skip_post: bool = False):
    """
    Single execution flow:
    1. Generate 1 prompt with Grok
    2. Generate 1 video with Runpod
    3. Post to Later (if configured)
    """

    # Get account config
    account = get_account(account_id)
    print(f"\n{'='*50}")
    print(f"Account: {account['name']}")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print(f"{'='*50}\n")

    # Override sheet name if specified
    if account.get("sheet_name"):
        os.environ["SHEET_NAME"] = account["sheet_name"]

    # --- Phase 1: Generate Prompt ---
    print("[1/3] Generating prompt with Grok...")

    # Get past prompts from Sheets to avoid repetition
    past_prompts = []
    try:
        all_rows = sheets_client.get_all_rows()
        past_prompts = [row["prompt"] for row in all_rows if row.get("prompt")]
        print(f"  Found {len(past_prompts)} past prompts to avoid")
    except Exception as e:
        print(f"  Warning: Could not fetch past prompts: {e}")

    try:
        prompts = grok_client.generate_prompts(
            count=1,
            style=account.get("style", "cinematic"),
            include_dialogue=True,
            theme=account.get("theme"),
            past_prompts=past_prompts,
        )

        if not prompts:
            raise Exception("No prompts generated")

        prompt_data = prompts[0]
        print(f"  Prompt: {prompt_data['prompt'][:80]}...")
        print(f"  Caption: {prompt_data['caption']}")

    except Exception as e:
        print(f"  ERROR: {e}")
        return {"status": "error", "phase": "prompt", "error": str(e)}

    # --- Save to Sheets ---
    print("\n[1.5/3] Saving to Sheets...")
    try:
        sheets_client.add_prompts([prompt_data])

        # Get the row ID (latest row)
        rows = sheets_client.get_all_rows()
        row_id = rows[-1]["id"] if rows else "1"
        print(f"  Saved as row {row_id}")

    except Exception as e:
        print(f"  WARNING: Could not save to Sheets: {e}")
        row_id = None

    # --- Phase 2: Generate Video ---
    print("\n[2/3] Generating video with Runpod...")

    try:
        # Submit job
        job_id = ltx_client.submit_job(
            prompt=prompt_data["prompt"],
            duration=DEFAULT_DURATION,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            steps=DEFAULT_STEPS,
        )
        print(f"  Job ID: {job_id}")

        # Update sheets
        if row_id:
            sheets_client.mark_generating(row_id, job_id)

        # Wait for completion
        print("  Waiting for completion...")
        result = ltx_client.wait_for_completion(job_id)

        output = result.get("output", {})
        exec_time = result.get("executionTime", 0) / 1000
        cost = exec_time * 0.00106

        print(f"  Duration: {output.get('duration')}s")
        print(f"  Resolution: {output.get('resolution')}")
        print(f"  Generation time: {exec_time:.1f}s")
        print(f"  Cost: ${cost:.4f}")

        # Get video bytes
        video_b64 = output.get("video_base64")
        if not video_b64:
            raise Exception("No video in response")

        video_bytes = base64.b64decode(video_b64)

        # Save video locally
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        video_filename = f"{account_id or DEFAULT_ACCOUNT}_{timestamp}.mp4"
        video_path = OUTPUT_DIR / video_filename
        video_path.write_bytes(video_bytes)
        print(f"  Saved: {video_path}")

        # Update sheets
        if row_id:
            sheets_client.mark_generated(
                row_id,
                video_url=f"job:{job_id}",
                duration=output.get("duration", 10),
                resolution=output.get("resolution", "576x1024"),
                cost=cost,
            )

    except Exception as e:
        print(f"  ERROR: {e}")
        if row_id:
            sheets_client.mark_error(row_id, str(e))
        return {"status": "error", "phase": "video", "error": str(e)}

    # --- Phase 3: Post to Later ---
    if skip_post:
        print("\n[3/3] Skipping post (--skip-post flag)")
        final_status = "generated"
    elif not LATER_AVAILABLE:
        print("\n[3/3] Later API not configured, skipping post")
        final_status = "generated"
    else:
        print("\n[3/3] Posting to Later...")
        try:
            # Build caption with hashtags
            caption = prompt_data.get("caption", "")
            hashtags = prompt_data.get("hashtags", [])
            if hashtags:
                caption += "\n\n" + " ".join(f"#{tag}" for tag in hashtags)

            # Upload and post
            result = later_client.schedule_video(
                video_bytes=video_bytes,
                caption=caption,
                hashtags=hashtags,
            )

            print(f"  Posted! Media ID: {result.get('media_id')}")

            # Update sheets
            if row_id:
                sheets_client.mark_scheduled(
                    row_id,
                    later_id=result.get("post_id", ""),
                    scheduled_at=datetime.utcnow().isoformat(),
                )

            final_status = "posted"

        except Exception as e:
            print(f"  WARNING: Could not post to Later: {e}")
            final_status = "generated"

    # --- Summary ---
    print(f"\n{'='*50}")
    print(f"COMPLETED: {final_status}")
    print(f"{'='*50}\n")

    return {
        "status": final_status,
        "account": account_id or DEFAULT_ACCOUNT,
        "prompt": prompt_data["prompt"][:100],
        "caption": prompt_data["caption"],
        "job_id": job_id,
        "cost": cost,
        "video_path": str(video_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Single video generation run")
    parser.add_argument(
        "--account", "-a",
        default=DEFAULT_ACCOUNT,
        help=f"Account ID to use. Available: {list_accounts()}",
    )
    parser.add_argument(
        "--skip-post",
        action="store_true",
        help="Skip posting to Later (generate only)",
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List available accounts and exit",
    )

    args = parser.parse_args()

    if args.list_accounts:
        print("Available accounts:")
        for acc_id in list_accounts():
            acc = get_account(acc_id)
            print(f"  - {acc_id}: {acc['name']}")
        return

    result = run_single(args.account, args.skip_post)

    if result["status"] == "error":
        exit(1)


if __name__ == "__main__":
    main()
