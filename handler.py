"""
LTX-2 Serverless Handler for Runpod
RTX 6000 Ada (48GB) - fp8 + LoRA
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
LTX2_PATH = f"{VOLUME_PATH}/LTX-2"
VENV_PYTHON = f"{LTX2_PATH}/.venv/bin/python"


def run_generation(
    prompt: str,
    output_path: str,
    negative_prompt: str = "",
    num_frames: int = 73,
    width: int = 1280,
    height: int = 720,
    seed: int = None,
    steps: int = 8,
):
    """LTX-2 CLIで動画生成"""

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

    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=LTX2_PATH,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise Exception(f"Generation failed: {result.stderr}")

    return output_path


def handler(job):
    """Runpod Serverless Handler"""

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

    # フレーム数計算 (8の倍数+1)
    num_frames = int(duration * fps)
    num_frames = ((num_frames - 1) // 8) * 8 + 1

    # 出力パス
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    job_id = str(uuid.uuid4())[:8]
    output_path = f"{OUTPUT_DIR}/{job_id}.mp4"

    try:
        print(f"Generating: {prompt[:50]}...")

        run_generation(
            prompt=prompt,
            output_path=output_path,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            width=width,
            height=height,
            seed=seed,
            steps=steps,
        )

        # Base64エンコード
        with open(output_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        # クリーンアップ
        os.remove(output_path)

        return {
            "status": "success",
            "video_base64": video_base64,
            "duration": duration,
            "resolution": f"{width}x{height}",
            "frames": num_frames,
        }

    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
