"""
LTX-2 Video Generation API Server
FastAPI + RTX A5000 (24GB)
CLI wrapper approach
"""

import os
import sys
import uuid
import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# パス設定
LTX2_PATH = "/workspace/LTX-2"
MODEL_DIR = os.environ.get("MODEL_DIR", "/workspace/models")
OUTPUT_DIR = "/workspace/outputs"
VENV_PYTHON = f"{LTX2_PATH}/.venv/bin/python"

# 生成ジョブ管理
jobs = {}


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="動画生成プロンプト")
    negative_prompt: str = Field(default="", description="ネガティブプロンプト")
    duration: float = Field(default=5, ge=1, le=10, description="動画長(秒)")
    width: int = Field(default=1280, description="幅")
    height: int = Field(default=720, description="高さ")
    fps: int = Field(default=24, description="フレームレート")
    seed: Optional[int] = Field(default=None, description="シード値")
    steps: int = Field(default=8, description="推論ステップ数")


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


def check_models():
    """必要なモデルファイルの確認"""
    required_files = [
        f"{MODEL_DIR}/ltx-2-19b-dev-fp8.safetensors",
        f"{MODEL_DIR}/ltx-2-19b-distilled-lora-384.safetensors",
        f"{MODEL_DIR}/ltx-2-spatial-upscaler-x2-1.0.safetensors",
    ]
    required_dirs = [
        f"{MODEL_DIR}/gemma",
    ]
    missing = [f for f in required_files if not os.path.exists(f)]
    missing += [d for d in required_dirs if not os.path.isdir(d)]
    return len(missing) == 0, missing


GEMMA_PATH = f"{MODEL_DIR}/gemma"


def run_generation(
    prompt: str,
    output_path: str,
    negative_prompt: str = "",
    num_frames: int = 121,
    width: int = 1280,
    height: int = 720,
    seed: Optional[int] = None,
    steps: int = 8,
):
    """LTX-2 CLIを使って動画生成"""

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時の初期化"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Starting LTX-2 API Server...")

    # モデル確認
    ok, missing = check_models()
    if not ok:
        print(f"Warning: Missing models: {missing}")
        print("Run download script first!")
    else:
        print("All models found!")

    yield
    print("Shutting down...")


app = FastAPI(
    title="LTX-2 Video Generation API",
    description="RTX A5000で動く動画生成API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    ok, missing = check_models()
    return {
        "service": "LTX-2 Video Generation API",
        "status": "running",
        "model": "LTX-2 19B fp8 + Distilled LoRA",
        "models_ready": ok,
        "missing_models": missing if not ok else [],
    }


@app.get("/health")
async def health():
    ok, missing = check_models()
    return {
        "status": "healthy" if ok else "models_missing",
        "models_ready": ok,
        "missing_models": missing if not ok else [],
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


@app.post("/generate", response_model=JobStatus)
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """動画生成（非同期）"""

    ok, missing = check_models()
    if not ok:
        raise HTTPException(status_code=503, detail=f"Missing models: {missing}")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "pending",
        "request": request.dict(),
    }

    background_tasks.add_task(process_generation, job_id, request)

    return JobStatus(
        job_id=job_id,
        status="pending",
        progress="Job queued",
    )


@app.post("/generate/sync")
async def generate_video_sync(request: GenerateRequest):
    """動画生成（同期・完了まで待つ）"""

    ok, missing = check_models()
    if not ok:
        raise HTTPException(status_code=503, detail=f"Missing models: {missing}")

    try:
        # フレーム数計算 (24fps, 8の倍数+1)
        num_frames = int(request.duration * request.fps)
        num_frames = ((num_frames - 1) // 8) * 8 + 1

        job_id = str(uuid.uuid4())[:8]
        output_path = f"{OUTPUT_DIR}/{job_id}.mp4"

        print(f"Generating: {request.prompt[:50]}...")

        run_generation(
            prompt=request.prompt,
            output_path=output_path,
            negative_prompt=request.negative_prompt,
            num_frames=num_frames,
            width=request.width,
            height=request.height,
            seed=request.seed,
            steps=request.steps,
        )

        # Base64エンコード
        with open(output_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        return {
            "status": "success",
            "job_id": job_id,
            "video_base64": video_base64,
            "duration": request.duration,
            "resolution": f"{request.width}x{request.height}",
            "frames": num_frames,
            "download_url": f"/download/{job_id}",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_generation(job_id: str, request: GenerateRequest):
    """バックグラウンド生成処理"""

    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = "Starting generation..."

        # フレーム数計算
        num_frames = int(request.duration * request.fps)
        num_frames = ((num_frames - 1) // 8) * 8 + 1

        jobs[job_id]["progress"] = f"Generating {num_frames} frames..."

        output_path = f"{OUTPUT_DIR}/{job_id}.mp4"

        run_generation(
            prompt=request.prompt,
            output_path=output_path,
            negative_prompt=request.negative_prompt,
            num_frames=num_frames,
            width=request.width,
            height=request.height,
            seed=request.seed,
            steps=request.steps,
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = "Done"
        jobs[job_id]["result"] = {
            "video_path": output_path,
            "download_url": f"/download/{job_id}",
            "duration": request.duration,
            "resolution": f"{request.width}x{request.height}",
            "frames": num_frames,
        }

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """ジョブステータス確認"""

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
    )


@app.get("/download/{job_id}")
async def download_video(job_id: str):
    """動画ダウンロード"""

    video_path = f"{OUTPUT_DIR}/{job_id}.mp4"

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
    )


@app.get("/jobs")
async def list_jobs():
    """ジョブ一覧"""
    return {
        "jobs": [
            {"job_id": jid, "status": j["status"]}
            for jid, j in jobs.items()
        ]
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
