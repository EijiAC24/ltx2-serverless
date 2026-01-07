"""
LTX-2 Runpod Serverless Client
"""

import time
import base64
import requests
from typing import Optional, Dict, Tuple

from config import (
    RUNPOD_API_KEY,
    RUNPOD_ENDPOINT,
    DEFAULT_DURATION,
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_STEPS,
    POLL_INTERVAL,
    MAX_POLL_TIME,
)


def submit_job(
    prompt: str,
    duration: float = DEFAULT_DURATION,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    steps: int = DEFAULT_STEPS,
    seed: Optional[int] = None,
    image_base64: Optional[str] = None,
    image_strength: float = 1.0,
) -> str:
    """
    Submit a video generation job (T2V or I2V)

    Args:
        prompt: Generation prompt
        duration: Video duration in seconds
        width: Video width (must be divisible by 64)
        height: Video height (must be divisible by 64)
        steps: Inference steps (20 recommended)
        seed: Random seed for reproducibility
        image_base64: Base64 encoded image for I2V (optional, None for T2V)
        image_strength: Image conditioning strength 0.0-1.0 (default 1.0)

    Returns:
        Job ID
    """
    if not RUNPOD_API_KEY:
        raise ValueError("RUNPOD_API_KEY not set")

    # Validate resolution
    if width % 64 != 0 or height % 64 != 0:
        raise ValueError(f"Resolution {width}x{height} must be divisible by 64")

    payload = {
        "input": {
            "prompt": prompt,
            "duration": duration,
            "width": width,
            "height": height,
            "steps": steps,
        }
    }

    if seed is not None:
        payload["input"]["seed"] = seed

    # I2V: 画像入力
    if image_base64:
        payload["input"]["image_base64"] = image_base64
        payload["input"]["image_strength"] = image_strength

    response = requests.post(
        f"{RUNPOD_ENDPOINT}/run",
        headers={
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    response.raise_for_status()
    result = response.json()

    return result["id"]


def get_status(job_id: str) -> Dict:
    """Get job status"""
    response = requests.get(
        f"{RUNPOD_ENDPOINT}/status/{job_id}",
        headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def wait_for_completion(job_id: str) -> Dict:
    """
    Wait for job to complete

    Returns:
        Full response dict with output
    """
    start_time = time.time()

    while time.time() - start_time < MAX_POLL_TIME:
        status = get_status(job_id)
        state = status.get("status")

        if state == "COMPLETED":
            return status
        elif state == "FAILED":
            error = status.get("error", "Unknown error")
            raise Exception(f"Job failed: {error}")
        elif state in ("IN_QUEUE", "IN_PROGRESS"):
            print(f"Job {job_id}: {state}...")
            time.sleep(POLL_INTERVAL)
        else:
            print(f"Job {job_id}: Unknown status {state}")
            time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Job {job_id} timed out after {MAX_POLL_TIME}s")


def generate_video(
    prompt: str,
    duration: float = DEFAULT_DURATION,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    steps: int = DEFAULT_STEPS,
    seed: Optional[int] = None,
    image_base64: Optional[str] = None,
    image_strength: float = 1.0,
) -> Tuple[bytes, Dict]:
    """
    Generate video and return bytes (T2V or I2V)

    Returns:
        Tuple of (video_bytes, metadata)
    """
    job_id = submit_job(prompt, duration, width, height, steps, seed, image_base64, image_strength)
    mode = "I2V" if image_base64 else "T2V"
    print(f"[{mode}] Submitted job: {job_id}")

    result = wait_for_completion(job_id)
    output = result.get("output", {})

    video_b64 = output.get("video_base64")
    if not video_b64:
        raise Exception("No video in response")

    video_bytes = base64.b64decode(video_b64)

    metadata = {
        "job_id": job_id,
        "duration": output.get("duration"),
        "resolution": output.get("resolution"),
        "frames": output.get("frames"),
        "execution_time": result.get("executionTime", 0) / 1000,  # ms to seconds
    }

    # Calculate cost ($0.00106/sec)
    metadata["cost"] = round(metadata["execution_time"] * 0.00106, 4)

    return video_bytes, metadata


def generate_video_async(
    prompt: str,
    duration: float = DEFAULT_DURATION,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    steps: int = DEFAULT_STEPS,
    seed: Optional[int] = None,
    image_base64: Optional[str] = None,
    image_strength: float = 1.0,
) -> str:
    """
    Submit job without waiting (T2V or I2V)

    Returns:
        Job ID
    """
    return submit_job(prompt, duration, width, height, steps, seed, image_base64, image_strength)


def image_to_base64(image_path: str) -> str:
    """
    画像ファイルをBase64エンコード

    Args:
        image_path: 画像ファイルのパス

    Returns:
        Base64エンコードされた文字列
    """
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_video_from_image(
    image_path: str,
    prompt: str,
    duration: float = DEFAULT_DURATION,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    steps: int = DEFAULT_STEPS,
    seed: Optional[int] = None,
    image_strength: float = 1.0,
) -> Tuple[bytes, Dict]:
    """
    画像から動画を生成 (I2V convenience function)

    Args:
        image_path: 入力画像のパス
        prompt: 動きの説明プロンプト
        その他: generate_videoと同じ

    Returns:
        Tuple of (video_bytes, metadata)
    """
    image_b64 = image_to_base64(image_path)
    return generate_video(
        prompt=prompt,
        duration=duration,
        width=width,
        height=height,
        steps=steps,
        seed=seed,
        image_base64=image_b64,
        image_strength=image_strength,
    )


def check_health() -> bool:
    """Check endpoint health"""
    try:
        response = requests.get(
            f"{RUNPOD_ENDPOINT}/health",
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=10,
        )
        return response.status_code == 200
    except Exception:
        return False


if __name__ == "__main__":
    # Test
    print("Checking health...")
    if check_health():
        print("Endpoint is healthy")
    else:
        print("Endpoint not responding")
