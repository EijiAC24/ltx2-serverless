"""
Later API Client for social media scheduling

Note: Later API details may need adjustment based on actual API documentation.
This is a template implementation.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict

from config import LATER_API_KEY, LATER_PROFILE_ID

# Later API base URL (adjust based on actual API)
LATER_BASE_URL = "https://api.later.com/v1"


def get_headers() -> Dict:
    """Get auth headers"""
    return {
        "Authorization": f"Bearer {LATER_API_KEY}",
        "Content-Type": "application/json",
    }


def upload_media(video_bytes: bytes, filename: str = "video.mp4") -> str:
    """
    Upload video to Later

    Returns:
        Media ID
    """
    if not LATER_API_KEY:
        raise ValueError("LATER_API_KEY not set")

    # Later typically requires multipart upload
    response = requests.post(
        f"{LATER_BASE_URL}/media",
        headers={"Authorization": f"Bearer {LATER_API_KEY}"},
        files={"file": (filename, video_bytes, "video/mp4")},
        timeout=120,
    )

    response.raise_for_status()
    result = response.json()

    return result.get("id") or result.get("media_id")


def schedule_post(
    media_id: str,
    caption: str,
    scheduled_time: Optional[datetime] = None,
    profile_id: Optional[str] = None,
) -> Dict:
    """
    Schedule a post

    Args:
        media_id: Later media ID
        caption: Post caption
        scheduled_time: When to post (default: next available slot)
        profile_id: Social profile ID (default from config)

    Returns:
        Post details including post_id
    """
    if not LATER_API_KEY:
        raise ValueError("LATER_API_KEY not set")

    profile = profile_id or LATER_PROFILE_ID
    if not profile:
        raise ValueError("LATER_PROFILE_ID not set")

    # Default to tomorrow 9am if not specified
    if scheduled_time is None:
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

    payload = {
        "media_id": media_id,
        "profile_id": profile,
        "caption": caption,
        "scheduled_time": scheduled_time.isoformat(),
    }

    response = requests.post(
        f"{LATER_BASE_URL}/posts",
        headers=get_headers(),
        json=payload,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def schedule_video(
    video_bytes: bytes,
    caption: str,
    hashtags: list = None,
    scheduled_time: Optional[datetime] = None,
) -> Dict:
    """
    Upload and schedule video in one step

    Returns:
        Dict with media_id, post_id, scheduled_time
    """
    # Build full caption with hashtags
    full_caption = caption
    if hashtags:
        tags = " ".join(f"#{tag}" for tag in hashtags if not tag.startswith("#"))
        full_caption = f"{caption}\n\n{tags}"

    # Upload
    print("Uploading video to Later...")
    media_id = upload_media(video_bytes)
    print(f"Uploaded: {media_id}")

    # Schedule
    print("Scheduling post...")
    post = schedule_post(media_id, full_caption, scheduled_time)
    print(f"Scheduled: {post.get('id')}")

    return {
        "media_id": media_id,
        "post_id": post.get("id"),
        "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
    }


def get_scheduled_posts() -> list:
    """Get all scheduled posts"""
    response = requests.get(
        f"{LATER_BASE_URL}/posts",
        headers=get_headers(),
        params={"status": "scheduled"},
        timeout=30,
    )

    response.raise_for_status()
    return response.json().get("posts", [])


def delete_post(post_id: str) -> bool:
    """Delete a scheduled post"""
    response = requests.delete(
        f"{LATER_BASE_URL}/posts/{post_id}",
        headers=get_headers(),
        timeout=30,
    )

    return response.status_code == 200


def get_profiles() -> list:
    """Get connected social profiles"""
    response = requests.get(
        f"{LATER_BASE_URL}/profiles",
        headers=get_headers(),
        timeout=30,
    )

    response.raise_for_status()
    return response.json().get("profiles", [])


if __name__ == "__main__":
    # Test - list profiles
    try:
        profiles = get_profiles()
        print(f"Connected profiles: {len(profiles)}")
        for p in profiles:
            print(f"  - {p.get('platform')}: {p.get('username')}")
    except Exception as e:
        print(f"Error: {e}")
