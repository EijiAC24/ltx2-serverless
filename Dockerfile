# LTX-2 Serverless Worker for Runpod
# Network Volume版 - RTX 6000 Ada (48GB)
# LTX-2とモデルはNetwork Volumeに配置済み

FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /workspace

# 最小限の依存関係
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Runpod SDK
RUN pip install runpod

# ハンドラーコピー
COPY handler.py /workspace/handler.py

ENV PYTHONUNBUFFERED=1

# Network VolumeのvenvからPythonを使用
# /runpod-volume/LTX-2/.venv/bin/python
CMD ["python", "-u", "handler.py"]
