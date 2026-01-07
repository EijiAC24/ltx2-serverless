"""
FTP Client for uploading videos to Lolipop server
"""

import ftplib
import os
from pathlib import Path
from typing import Optional
from config import FTP_SERVER, FTP_USER, FTP_PASSWORD, FTP_PATH


def upload_video(video_bytes: bytes, filename: str, account_id: str = "") -> str:
    """
    Upload video to FTP server

    Args:
        video_bytes: Video file content
        filename: Name of the file (e.g., "video_001.mp4")
        account_id: Account ID (used for organizing, path is from FTP_PATH env var)

    Returns:
        URL of uploaded file
    """
    if not all([FTP_SERVER, FTP_USER, FTP_PASSWORD]):
        raise ValueError("FTP credentials not configured")

    # Connect to FTP
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASSWORD)

    # Use FTP_PATH directly (should include account folder)
    target_path = FTP_PATH

    # Create directory if needed
    try:
        ftp.cwd(target_path)
    except ftplib.error_perm:
        # Directory doesn't exist, create it
        _makedirs(ftp, target_path)
        ftp.cwd(target_path)

    # Upload file
    from io import BytesIO
    ftp.storbinary(f"STOR {filename}", BytesIO(video_bytes))

    ftp.quit()

    # Return URL
    base_url = os.environ.get("FTP_BASE_URL", "http://okibai.heavy.jp")
    return f"{base_url}{FTP_PATH}/{filename}"


def _makedirs(ftp: ftplib.FTP, path: str):
    """Create directory tree on FTP"""
    parts = path.strip("/").split("/")
    current = ""
    for part in parts:
        current += f"/{part}"
        try:
            ftp.mkd(current)
        except ftplib.error_perm:
            pass  # Directory exists


def list_videos() -> list:
    """
    List video files on FTP server

    Returns:
        List of filenames
    """
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASSWORD)

    try:
        ftp.cwd(FTP_PATH)
        files = ftp.nlst()
        videos = [f for f in files if f.endswith(".mp4")]
    except ftplib.error_perm:
        videos = []

    ftp.quit()
    return videos


def download_video(filename: str) -> bytes:
    """
    Download video from FTP server

    Returns:
        Video bytes
    """
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASSWORD)

    ftp.cwd(FTP_PATH)

    from io import BytesIO
    buffer = BytesIO()
    ftp.retrbinary(f"RETR {filename}", buffer.write)

    ftp.quit()
    return buffer.getvalue()


def delete_video(filename: str) -> bool:
    """Delete video from FTP server"""
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASSWORD)

    try:
        ftp.cwd(FTP_PATH)
        ftp.delete(filename)
        ftp.quit()
        return True
    except ftplib.error_perm:
        ftp.quit()
        return False


if __name__ == "__main__":
    # Test listing
    from dotenv import load_dotenv
    load_dotenv()

    print(f"FTP Path: {FTP_PATH}")
    print("Videos on server:")
    for v in list_videos():
        print(f"  - {v}")
