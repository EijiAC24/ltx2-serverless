"""
LTX-2 Video Generation Client
Pods API Server 用
"""

import os
import time
import base64
import requests
import argparse


def generate_video_sync(
    server_url: str,
    prompt: str,
    negative_prompt: str = "",
    duration: int = 10,
    width: int = 1920,
    height: int = 1080,
    seed: int = None,
    output_path: str = "output.mp4",
):
    """動画生成（同期・完了まで待つ）"""

    url = f"{server_url}/generate/sync"

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "duration": duration,
        "width": width,
        "height": height,
        "seed": seed,
    }

    print(f"Server: {server_url}")
    print(f"Prompt: {prompt}")
    print(f"Duration: {duration}s @ {width}x{height}")
    print("Generating...")

    start_time = time.time()
    response = requests.post(url, json=payload, timeout=600)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

    result = response.json()

    if result.get("status") != "success":
        print(f"Error: {result.get('error')}")
        return None

    # 動画をデコードして保存
    video_base64 = result.get("video_base64")
    if video_base64:
        video_data = base64.b64decode(video_base64)
        with open(output_path, "wb") as f:
            f.write(video_data)

        elapsed = time.time() - start_time
        print(f"Saved: {output_path}")
        print(f"Time: {elapsed:.1f}s")
        return output_path

    return None


def generate_video_async(
    server_url: str,
    prompt: str,
    negative_prompt: str = "",
    duration: int = 10,
    width: int = 1920,
    height: int = 1080,
    seed: int = None,
    output_path: str = "output.mp4",
    poll_interval: int = 5,
):
    """動画生成（非同期・ポーリング）"""

    # ジョブ投入
    url = f"{server_url}/generate"
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "duration": duration,
        "width": width,
        "height": height,
        "seed": seed,
    }

    print(f"Server: {server_url}")
    print(f"Prompt: {prompt}")

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    job_id = response.json().get("job_id")
    print(f"Job ID: {job_id}")

    # ステータスポーリング
    start_time = time.time()
    while True:
        status_url = f"{server_url}/status/{job_id}"
        status_resp = requests.get(status_url)
        status = status_resp.json()

        print(f"  Status: {status['status']} - {status.get('progress', '')}")

        if status["status"] == "completed":
            # ダウンロード
            download_url = f"{server_url}/download/{job_id}"
            video_resp = requests.get(download_url)
            with open(output_path, "wb") as f:
                f.write(video_resp.content)

            elapsed = time.time() - start_time
            print(f"Saved: {output_path}")
            print(f"Time: {elapsed:.1f}s")
            return output_path

        elif status["status"] == "failed":
            print(f"Error: {status.get('error')}")
            return None

        time.sleep(poll_interval)


def check_health(server_url: str):
    """サーバーヘルスチェック"""
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            info = response.json()
            print(f"Status: {info['status']}")
            print(f"Model loaded: {info['model_loaded']}")
            print(f"GPU: {info['gpu_name']}")
            return True
    except Exception as e:
        print(f"Server not reachable: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(description="LTX-2 Video Generation Client")
    parser.add_argument("--server", type=str, help="Server URL (e.g., http://xxx.runpod.io:8000)")
    parser.add_argument("--prompt", type=str, help="生成プロンプト")
    parser.add_argument("--negative_prompt", type=str, default="", help="ネガティブプロンプト")
    parser.add_argument("--duration", type=int, default=10, help="動画長(秒)")
    parser.add_argument("--width", type=int, default=1920, help="幅")
    parser.add_argument("--height", type=int, default=1080, help="高さ")
    parser.add_argument("--seed", type=int, default=None, help="シード値")
    parser.add_argument("--output", type=str, default="output.mp4", help="出力ファイル")
    parser.add_argument("--async", dest="async_mode", action="store_true", help="非同期モード")
    parser.add_argument("--health", action="store_true", help="ヘルスチェックのみ")
    args = parser.parse_args()

    # 環境変数からも取得可能
    server_url = args.server or os.environ.get("LTX2_SERVER_URL")

    if not server_url:
        print("Error: --server または LTX2_SERVER_URL 環境変数が必要")
        print("例: --server http://xxx-8000.proxy.runpod.net")
        return

    # ヘルスチェック
    if args.health:
        check_health(server_url)
        return

    if not args.prompt:
        print("Error: --prompt が必要")
        return

    # 生成
    if args.async_mode:
        generate_video_async(
            server_url=server_url,
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            duration=args.duration,
            width=args.width,
            height=args.height,
            seed=args.seed,
            output_path=args.output,
        )
    else:
        generate_video_sync(
            server_url=server_url,
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            duration=args.duration,
            width=args.width,
            height=args.height,
            seed=args.seed,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
