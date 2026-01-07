"""
バッチ動画生成スクリプト
複数のプロンプトから一括生成
"""

import os
import json
from datetime import datetime
from runpod_client import generate_and_download, health_check

# 生成するプロンプトリスト
PROMPTS = [
    "A cat walking in a garden, cinematic lighting",
    "Ocean waves crashing on a beach at sunset",
    "A city street at night with neon lights",
    "A forest path with sunlight filtering through trees",
    "A snow-covered mountain landscape",
]

# 出力設定
OUTPUT_DIR = "./outputs"
DURATION = 3  # 秒
WIDTH = 1280
HEIGHT = 768


def batch_generate():
    """バッチ生成"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ヘルスチェック
    health = health_check()
    if health.get("status") != "healthy":
        print(f"Server not healthy: {health}")
        return

    print(f"Server: {health.get('gpu')}")
    print(f"Generating {len(PROMPTS)} videos...")
    print("-" * 50)

    results = []
    for i, prompt in enumerate(PROMPTS):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{OUTPUT_DIR}/video_{i+1}_{timestamp}.mp4"

        try:
            print(f"\n[{i+1}/{len(PROMPTS)}] {prompt[:40]}...")
            status = generate_and_download(
                prompt=prompt,
                output_path=output_path,
                duration=DURATION,
                width=WIDTH,
                height=HEIGHT,
            )
            results.append({
                "prompt": prompt,
                "output": output_path,
                "status": "success",
            })
            print(f"Success: {output_path}")

        except Exception as e:
            results.append({
                "prompt": prompt,
                "status": "failed",
                "error": str(e),
            })
            print(f"Failed: {e}")

    # 結果サマリー
    print("\n" + "=" * 50)
    print("BATCH COMPLETE")
    print("=" * 50)

    success = sum(1 for r in results if r["status"] == "success")
    print(f"Success: {success}/{len(PROMPTS)}")

    # 結果をJSONに保存
    with open(f"{OUTPUT_DIR}/batch_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    batch_generate()
