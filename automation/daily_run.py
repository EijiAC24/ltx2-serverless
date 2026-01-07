"""
Daily Automation Script - runs all phases

Usage:
    python daily_run.py              # Run all phases
    python daily_run.py --prompts    # Generate prompts only
    python daily_run.py --videos     # Generate videos only
    python daily_run.py --schedule   # Schedule posts only
"""

import argparse
import sys
from datetime import datetime, timedelta

from config import DAILY_PROMPT_COUNT, DAILY_VIDEO_COUNT
import grok_client
import sheets_client
import ltx_client
import later_client


# Default categories for prompt generation
DEFAULT_CATEGORIES = [
    "cute animals",
    "vintage documentary",
    "nature scenery",
    "comedic moments",
]


def phase1_generate_prompts(categories: list = None, count: int = None):
    """Phase 1: Generate prompts with Grok and save to Sheets"""
    print("\n" + "=" * 50)
    print("PHASE 1: Generate Prompts")
    print("=" * 50)

    categories = categories or DEFAULT_CATEGORIES
    count = count or DAILY_PROMPT_COUNT

    # Calculate prompts per category
    per_category = max(1, count // len(categories))

    all_prompts = []
    for category in categories:
        try:
            print(f"\nGenerating prompts for '{category}'...")
            prompts = grok_client.generate_prompts(
                category=category,
                count=per_category,
                include_dialogue=True,
            )
            all_prompts.extend(prompts)
            print(f"  Generated {len(prompts)} prompts")
        except Exception as e:
            print(f"  Error: {e}")

    if all_prompts:
        # Save to Sheets
        print(f"\nSaving {len(all_prompts)} prompts to Sheets...")
        added = sheets_client.add_prompts(all_prompts)
        print(f"  Added {added} rows")

    return all_prompts


def phase2_generate_videos(limit: int = None):
    """Phase 2: Generate videos for pending prompts"""
    print("\n" + "=" * 50)
    print("PHASE 2: Generate Videos")
    print("=" * 50)

    limit = limit or DAILY_VIDEO_COUNT

    # Get pending prompts
    pending = sheets_client.get_rows_by_status("pending")
    print(f"\nFound {len(pending)} pending prompts")

    if not pending:
        print("No pending prompts to process")
        return []

    # Limit to daily count
    to_process = pending[:limit]
    print(f"Processing {len(to_process)} prompts...")

    results = []
    for row in to_process:
        row_id = row["id"]
        prompt = row["prompt"]

        print(f"\n[{row_id}] {prompt[:50]}...")

        try:
            # Mark as generating
            sheets_client.mark_generating(row_id, "")

            # Submit job
            job_id = ltx_client.generate_video_async(prompt)
            sheets_client.update_row(row_id, {"job_id": job_id})
            print(f"  Submitted: {job_id}")

            # Wait for completion
            result = ltx_client.wait_for_completion(job_id)
            output = result.get("output", {})

            # Calculate cost
            exec_time = result.get("executionTime", 0) / 1000
            cost = round(exec_time * 0.00106, 4)

            # For now, store base64 reference (Later API will handle upload)
            # In production, upload to cloud storage and store URL
            video_url = f"job:{job_id}"

            sheets_client.mark_generated(
                row_id,
                video_url=video_url,
                duration=output.get("duration", 0),
                resolution=output.get("resolution", ""),
                cost=cost,
            )

            print(f"  Completed: {output.get('resolution')}, ${cost}")
            results.append({
                "row_id": row_id,
                "job_id": job_id,
                "status": "success",
            })

        except Exception as e:
            print(f"  Error: {e}")
            sheets_client.mark_error(row_id, str(e))
            results.append({
                "row_id": row_id,
                "status": "error",
                "error": str(e),
            })

    return results


def phase3_schedule_posts(limit: int = None):
    """Phase 3: Schedule generated videos to Later"""
    print("\n" + "=" * 50)
    print("PHASE 3: Schedule Posts")
    print("=" * 50)

    limit = limit or DAILY_VIDEO_COUNT

    # Get generated videos
    generated = sheets_client.get_rows_by_status("generated")
    print(f"\nFound {len(generated)} generated videos")

    if not generated:
        print("No videos to schedule")
        return []

    to_schedule = generated[:limit]
    print(f"Scheduling {len(to_schedule)} videos...")

    # Calculate schedule times (spread throughout the day)
    base_time = datetime.utcnow() + timedelta(days=1)
    base_time = base_time.replace(hour=9, minute=0, second=0, microsecond=0)

    results = []
    for i, row in enumerate(to_schedule):
        row_id = row["id"]
        job_id = row.get("video_url", "").replace("job:", "")
        caption = row.get("caption", "")
        hashtags = row.get("hashtags", "").split(",") if row.get("hashtags") else []

        # Schedule 2 hours apart
        scheduled_time = base_time + timedelta(hours=i * 2)

        print(f"\n[{row_id}] Scheduling for {scheduled_time}...")

        try:
            # Get video from Runpod (still in cache)
            status = ltx_client.get_status(job_id)
            if status.get("status") != "COMPLETED":
                raise Exception("Video no longer available")

            import base64
            video_b64 = status.get("output", {}).get("video_base64")
            if not video_b64:
                raise Exception("No video data")

            video_bytes = base64.b64decode(video_b64)

            # Upload and schedule
            result = later_client.schedule_video(
                video_bytes=video_bytes,
                caption=caption,
                hashtags=hashtags,
                scheduled_time=scheduled_time,
            )

            sheets_client.mark_scheduled(
                row_id,
                later_id=result.get("post_id", ""),
                scheduled_at=scheduled_time.isoformat(),
            )

            print(f"  Scheduled: {result.get('post_id')}")
            results.append({
                "row_id": row_id,
                "status": "scheduled",
                "scheduled_time": scheduled_time.isoformat(),
            })

        except Exception as e:
            print(f"  Error: {e}")
            sheets_client.mark_error(row_id, f"Schedule failed: {e}")
            results.append({
                "row_id": row_id,
                "status": "error",
                "error": str(e),
            })

    return results


def run_all():
    """Run all phases"""
    print("\n" + "#" * 60)
    print("# LTX-2 Daily Automation")
    print(f"# {datetime.utcnow().isoformat()}")
    print("#" * 60)

    # Initialize sheet if needed
    try:
        sheets_client.init_sheet()
    except Exception as e:
        print(f"Warning: Could not init sheet: {e}")

    # Phase 1: Generate prompts
    prompts = phase1_generate_prompts()
    print(f"\nPhase 1 complete: {len(prompts)} prompts generated")

    # Phase 2: Generate videos
    videos = phase2_generate_videos()
    success = sum(1 for v in videos if v.get("status") == "success")
    print(f"\nPhase 2 complete: {success}/{len(videos)} videos generated")

    # Phase 3: Schedule posts
    posts = phase3_schedule_posts()
    scheduled = sum(1 for p in posts if p.get("status") == "scheduled")
    print(f"\nPhase 3 complete: {scheduled}/{len(posts)} posts scheduled")

    print("\n" + "#" * 60)
    print("# Automation Complete")
    print("#" * 60)

    return {
        "prompts": len(prompts),
        "videos_success": success,
        "videos_total": len(videos),
        "scheduled": scheduled,
    }


def main():
    parser = argparse.ArgumentParser(description="LTX-2 Daily Automation")
    parser.add_argument("--prompts", action="store_true", help="Generate prompts only")
    parser.add_argument("--videos", action="store_true", help="Generate videos only")
    parser.add_argument("--schedule", action="store_true", help="Schedule posts only")
    parser.add_argument("--count", type=int, help="Override daily count")

    args = parser.parse_args()
    count = args.count

    if args.prompts:
        phase1_generate_prompts(count=count)
    elif args.videos:
        phase2_generate_videos(limit=count)
    elif args.schedule:
        phase3_schedule_posts(limit=count)
    else:
        run_all()


if __name__ == "__main__":
    main()
