"""
LTX-2 Runpod Client
Pod管理 + 動画生成API
"""

import os
import time
import requests
import runpod

# 設定
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "your_api_key_here")
POD_ID = "i8k4ha2yjgdaep"  # 現在のPod ID
API_PORT = 8000

runpod.api_key = RUNPOD_API_KEY


def get_pod_status():
    """Podのステータス取得"""
    pod = runpod.get_pod(POD_ID)
    return pod


def get_api_url():
    """API URLを取得"""
    return f"https://{POD_ID}-{API_PORT}.proxy.runpod.net"


def health_check():
    """ヘルスチェック"""
    url = f"{get_api_url()}/health"
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return {"status": "unavailable"}


def generate_video(
    prompt: str,
    duration: float = 3,
    width: int = 1280,
    height: int = 768,
    negative_prompt: str = "",
    seed: int = None,
    steps: int = 8,
):
    """動画生成ジョブを投入"""
    url = f"{get_api_url()}/generate"
    data = {
        "prompt": prompt,
        "duration": duration,
        "width": width,
        "height": height,
        "negative_prompt": negative_prompt,
        "steps": steps,
    }
    if seed is not None:
        data["seed"] = seed

    r = requests.post(url, json=data, timeout=30)
    return r.json()


def get_job_status(job_id: str):
    """ジョブステータス確認"""
    url = f"{get_api_url()}/status/{job_id}"
    r = requests.get(url, timeout=10)
    return r.json()


def wait_for_completion(job_id: str, poll_interval: int = 10, timeout: int = 600):
    """ジョブ完了を待つ"""
    start = time.time()
    while time.time() - start < timeout:
        status = get_job_status(job_id)
        print(f"Status: {status['status']}")

        if status["status"] == "completed":
            return status
        elif status["status"] == "failed":
            raise Exception(f"Job failed: {status.get('error')}")

        time.sleep(poll_interval)

    raise TimeoutError("Job timed out")


def download_video(job_id: str, output_path: str):
    """動画をダウンロード"""
    url = f"{get_api_url()}/download/{job_id}"
    r = requests.get(url, timeout=60)

    with open(output_path, "wb") as f:
        f.write(r.content)

    print(f"Downloaded: {output_path}")
    return output_path


def generate_and_download(
    prompt: str,
    output_path: str,
    duration: float = 3,
    width: int = 1280,
    height: int = 768,
    **kwargs
):
    """動画生成してダウンロードまで"""
    print(f"Generating: {prompt[:50]}...")

    # ジョブ投入
    result = generate_video(prompt, duration, width, height, **kwargs)
    job_id = result["job_id"]
    print(f"Job ID: {job_id}")

    # 完了待ち
    status = wait_for_completion(job_id)

    # ダウンロード
    download_video(job_id, output_path)

    return status


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LTX-2 Video Generator")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--prompt", type=str, help="Video prompt")
    parser.add_argument("--output", type=str, default="output.mp4", help="Output path")
    parser.add_argument("--duration", type=float, default=3, help="Duration (seconds)")
    parser.add_argument("--width", type=int, default=1280, help="Width")
    parser.add_argument("--height", type=int, default=768, help="Height")

    args = parser.parse_args()

    if args.health:
        print(health_check())
    elif args.prompt:
        generate_and_download(
            args.prompt,
            args.output,
            args.duration,
            args.width,
            args.height,
        )
    else:
        parser.print_help()
