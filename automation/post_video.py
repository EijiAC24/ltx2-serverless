"""
Post Video: Download from FTP and post to Later API
Designed to run separately from video generation
"""

import argparse
import os
from datetime import datetime, timezone

# Load .env for local testing
from dotenv import load_dotenv
load_dotenv()

from accounts import get_account, list_accounts, DEFAULT_ACCOUNT
import ftp_client
import sheets_client
import later_client


def get_pending_videos() -> list:
    """
    Get videos that are generated but not yet posted

    Returns videos from Sheets with status='generated'
    """
    try:
        rows = sheets_client.get_all_rows()
        pending = [r for r in rows if r.get("status") == "generated"]
        return pending
    except Exception as e:
        print(f"Warning: Could not fetch from Sheets: {e}")
        return []


def post_single(video_url: str = None, row_id: str = None, dry_run: bool = False):
    """
    Post a single video to Later

    Args:
        video_url: Direct URL to video on FTP
        row_id: Sheets row ID (will get video_url from there)
        dry_run: If True, just show what would be posted
    """
    print(f"\n{'='*50}")
    print(f"POST VIDEO")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*50}\n")

    # Get video info from Sheets if row_id provided
    if row_id:
        try:
            rows = sheets_client.get_all_rows()
            row = next((r for r in rows if r["id"] == row_id), None)
            if not row:
                print(f"ERROR: Row {row_id} not found")
                return {"status": "error", "error": "Row not found"}

            video_url = row.get("video_url", "")
            caption = row.get("caption", "")
            hashtags = row.get("hashtags", "").split(",") if row.get("hashtags") else []

            print(f"Row ID: {row_id}")
            print(f"Caption: {caption}")
            print(f"Video URL: {video_url}")

        except Exception as e:
            print(f"ERROR: {e}")
            return {"status": "error", "error": str(e)}
    else:
        # No row_id - just use URL directly
        caption = ""
        hashtags = []

    if not video_url:
        print("ERROR: No video URL")
        return {"status": "error", "error": "No video URL"}

    # Extract filename from URL
    filename = video_url.split("/")[-1]
    print(f"Filename: {filename}")

    if dry_run:
        print("\n[DRY RUN] Would post this video to Later")
        return {"status": "dry_run", "filename": filename, "caption": caption}

    # Download video from FTP
    print("\n[1/3] Downloading from FTP...")
    try:
        video_bytes = ftp_client.download_video(filename)
        print(f"  Downloaded {len(video_bytes)/1024/1024:.2f} MB")
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"status": "error", "error": str(e)}

    # Post to Later
    print("\n[2/3] Posting to Later...")
    try:
        result = later_client.schedule_video(
            video_bytes=video_bytes,
            caption=caption,
            hashtags=hashtags,
        )
        print(f"  Posted! Media ID: {result.get('media_id')}")
    except Exception as e:
        print(f"  ERROR: {e}")
        if row_id:
            sheets_client.mark_error(row_id, f"Later: {str(e)}")
        return {"status": "error", "error": str(e)}

    # Update Sheets
    print("\n[3/3] Updating Sheets...")
    if row_id:
        try:
            sheets_client.mark_scheduled(
                row_id,
                later_id=result.get("post_id", ""),
                scheduled_at=datetime.now(timezone.utc).isoformat(),
            )
            print("  Updated")
        except Exception as e:
            print(f"  Warning: {e}")

    print(f"\n{'='*50}")
    print("POST COMPLETE")
    print(f"{'='*50}\n")

    return {
        "status": "posted",
        "filename": filename,
        "media_id": result.get("media_id"),
        "post_id": result.get("post_id"),
    }


def post_next(dry_run: bool = False):
    """Post the next pending video"""
    pending = get_pending_videos()

    if not pending:
        print("No pending videos to post")
        return {"status": "no_pending"}

    # Post the oldest one
    video = pending[0]
    print(f"Found {len(pending)} pending videos")
    print(f"Posting: Row {video['id']}")

    return post_single(row_id=video["id"], dry_run=dry_run)


def post_all(dry_run: bool = False, limit: int = 5):
    """Post all pending videos (up to limit)"""
    pending = get_pending_videos()

    if not pending:
        print("No pending videos to post")
        return {"status": "no_pending", "posted": 0}

    print(f"Found {len(pending)} pending videos")
    print(f"Will post up to {limit}\n")

    posted = 0
    for i, video in enumerate(pending[:limit]):
        print(f"\n--- Video {i+1}/{min(len(pending), limit)} ---")
        result = post_single(row_id=video["id"], dry_run=dry_run)
        if result["status"] == "posted":
            posted += 1

    return {"status": "completed", "posted": posted, "total": len(pending)}


def main():
    parser = argparse.ArgumentParser(description="Post videos to Later")
    parser.add_argument(
        "--row", "-r",
        help="Specific row ID to post",
    )
    parser.add_argument(
        "--url", "-u",
        help="Direct video URL to post",
    )
    parser.add_argument(
        "--next", "-n",
        action="store_true",
        help="Post the next pending video",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Post all pending videos",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Max videos to post with --all (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be posted without posting",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List pending videos",
    )

    args = parser.parse_args()

    if args.list:
        pending = get_pending_videos()
        print(f"Pending videos: {len(pending)}")
        for v in pending:
            print(f"  [{v['id']}] {v.get('caption', 'No caption')[:50]}")
        return

    if args.row:
        post_single(row_id=args.row, dry_run=args.dry_run)
    elif args.url:
        post_single(video_url=args.url, dry_run=args.dry_run)
    elif args.all:
        post_all(dry_run=args.dry_run, limit=args.limit)
    elif args.next:
        post_next(dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
