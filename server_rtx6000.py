"""
LTX-2 Video Generation API Server
RTX 6000 Ada (48GB) - fp8 + LoRA
"""

import os
import uuid
import base64
import subprocess
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

MODEL_DIR = "/workspace/models"
OUTPUT_DIR = "/workspace/outputs"
LTX2_PATH = "/workspace/LTX-2"
VENV_PYTHON = f"{LTX2_PATH}/.venv/bin/python"
GEMMA_PATH = f"{MODEL_DIR}/gemma"

jobs = {}

class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    duration: float = Field(default=3, ge=1, le=10)
    width: int = 1280
    height: int = 768
    fps: int = 24
    seed: Optional[int] = None
    steps: int = 8

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

def run_generation(prompt, output_path, negative_prompt="", num_frames=65, width=1280, height=768, seed=None, steps=8):
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

    result = subprocess.run(cmd, cwd=LTX2_PATH, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise Exception(f"Generation failed: {result.stderr}")
    return output_path

app = FastAPI(title="LTX-2 API", version="1.0")

@app.get("/")
async def root():
    return {"service": "LTX-2 API", "status": "running", "gpu": "RTX 6000 Ada"}

@app.get("/health")
async def health():
    return {"status": "healthy", "cuda": torch.cuda.is_available(), "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}

@app.post("/generate", response_model=JobStatus)
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(process_job, job_id, request)
    return JobStatus(job_id=job_id, status="pending", progress="Queued")

async def process_job(job_id: str, request: GenerateRequest):
    try:
        jobs[job_id]["status"] = "processing"
        num_frames = int(request.duration * request.fps)
        num_frames = ((num_frames - 1) // 8) * 8 + 1
        output_path = f"{OUTPUT_DIR}/{job_id}.mp4"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        run_generation(request.prompt, output_path, request.negative_prompt, num_frames, request.width, request.height, request.seed, request.steps)
        jobs[job_id] = {"status": "completed", "result": {"path": output_path, "download": f"/download/{job_id}"}}
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.get("/status/{job_id}", response_model=JobStatus)
async def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    j = jobs[job_id]
    return JobStatus(job_id=job_id, status=j["status"], result=j.get("result"), error=j.get("error"))

@app.get("/download/{job_id}")
async def download(job_id: str):
    path = f"{OUTPUT_DIR}/{job_id}.mp4"
    if not os.path.exists(path):
        raise HTTPException(404, "Video not found")
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")

@app.get("/jobs")
async def list_jobs():
    return {"jobs": [{"id": k, "status": v["status"]} for k, v in jobs.items()]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
