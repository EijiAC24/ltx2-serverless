"""
LTX-2 Serverless Handler for Runpod
RTX 6000 Ada (48GB) - fp8 + LoRA
Supports: Text-to-Video (T2V) and Image-to-Video (I2V)
"""

import os
import subprocess
import base64
import uuid
import runpod

# パス設定（Network Volume）
VOLUME_PATH = "/runpod-volume"
MODEL_DIR = f"{VOLUME_PATH}/models"
GEMMA_PATH = f"{MODEL_DIR}/gemma"
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
LTX2_PATH = f"{VOLUME_PATH}/LTX-2"
VENV_PYTHON = f"{LTX2_PATH}/.venv/bin/python"

# LTX-2 パッケージパスを環境変数に追加
os.environ["PYTHONPATH"] = f"{LTX2_PATH}/packages/ltx-pipelines/src:{LTX2_PATH}/packages/ltx-core/src:" + os.environ.get("PYTHONPATH", "")


def run_generation(
    prompt: str,
    output_path: str,
    negative_prompt: str = "",
    num_frames: int = 73,
    width: int = 1280,
    height: int = 720,
    seed: int = None,
    steps: int = 8,
    image_path: str = None,
    image_strength: float = 1.0,
):
    """
    LTX-2 CLIで動画生成

    Args:
        image_path: I2V用の入力画像パス（Noneの場合はT2V）
        image_strength: 画像の影響度（0.0-1.0、デフォルト1.0）
    """

    cmd = [
        VENV_PYTHON, "-m", "ltx_pipelines.ti2vid_two_stages",
        "--checkpoint-path", f"{MODEL_DIR}/ltx-2-19b-dev-fp8.safetensors",
        "--distilled-lora", f"{MODEL_DIR}/ltx-2-19b-distilled-lora-384.safetensors",
        "--spatial-upsampler-path", f"{MODEL_DIR}/ltx-2-spatial-upscaler-x2-1.0.safetensors",
        "--gemma-root", GEMMA_PATH,
        "--prompt", prompt,
        "--output-path", output_path,
        "--num-frames", str(num_frames),
        "--width", str(width),
        "--height", str(height),
        "--num-inference-steps", str(steps),
        "--enable-fp8",
    ]

    if negative_prompt:
        cmd.extend(["--negative-prompt", negative_prompt])

    if seed is not None:
        cmd.extend(["--seed", str(seed)])

    # I2V: 画像入力がある場合
    if image_path:
        cmd.extend(["--image", image_path, "0", str(image_strength)])

    print(f"Running: {' '.join(cmd)}")

    # 環境変数にPYTHONPATHを追加
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{LTX2_PATH}/packages/ltx-pipelines/src:{LTX2_PATH}/packages/ltx-core/src:" + env.get("PYTHONPATH", "")

    result = subprocess.run(
        cmd,
        cwd=LTX2_PATH,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )

    if result.returncode != 0:
        raise Exception(f"Generation failed: {result.stderr}")

    return output_path


def handler(job):
    """
    Runpod Serverless Handler

    Supports:
    - Text-to-Video (T2V): promptのみで動画生成
    - Image-to-Video (I2V): prompt + image_base64で画像から動画生成
    """

    job_input = job["input"]

    # 入力パラメータ
    prompt = job_input.get("prompt")
    if not prompt:
        return {"error": "prompt is required"}

    negative_prompt = job_input.get("negative_prompt", "")
    duration = job_input.get("duration", 3)
    width = job_input.get("width", 1280)
    height = job_input.get("height", 768)
    fps = job_input.get("fps", 24)
    seed = job_input.get("seed")
    steps = job_input.get("steps", 8)

    # I2V用パラメータ
    image_base64 = job_input.get("image_base64")
    image_strength = job_input.get("image_strength", 1.0)

    # フレーム数計算 (8の倍数+1)
    num_frames = int(duration * fps)
    num_frames = ((num_frames - 1) // 8) * 8 + 1

    # 出力パス
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INPUT_DIR, exist_ok=True)
    job_id = str(uuid.uuid4())[:8]
    output_path = f"{OUTPUT_DIR}/{job_id}.mp4"

    # I2V: 画像をデコードして保存
    image_path = None
    if image_base64:
        try:
            image_bytes = base64.b64decode(image_base64)
            image_path = f"{INPUT_DIR}/{job_id}.jpg"
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            print(f"I2V mode: saved input image to {image_path}")
        except Exception as e:
            return {"error": f"Failed to decode image: {str(e)}"}

    mode = "I2V" if image_path else "T2V"

    try:
        print(f"[{mode}] Generating: {prompt[:50]}...")

        run_generation(
            prompt=prompt,
            output_path=output_path,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            width=width,
            height=height,
            seed=seed,
            steps=steps,
            image_path=image_path,
            image_strength=image_strength,
        )

        # Base64エンコード
        with open(output_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        # クリーンアップ
        os.remove(output_path)
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

        return {
            "status": "success",
            "mode": mode,
            "video_base64": video_base64,
            "duration": duration,
            "resolution": f"{width}x{height}",
            "frames": num_frames,
        }

    except Exception as e:
        # エラー時もクリーンアップ
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
