# LTX-2 19B Serverless Worker for Runpod
# Network Volume版 - A6000 (48GB)

FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /workspace

# システム依存関係
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# uv インストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# LTX-2 クローン & セットアップ
RUN git clone https://github.com/Lightricks/LTX-2.git /workspace/LTX-2

WORKDIR /workspace/LTX-2

# 依存関係インストール
RUN uv sync --frozen

# Runpod SDK追加
RUN . /workspace/LTX-2/.venv/bin/activate && pip install runpod

# ハンドラーコピー
COPY handler.py /workspace/handler.py

# 環境変数
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# venv内のPythonでハンドラー起動
CMD ["/workspace/LTX-2/.venv/bin/python", "-u", "handler.py"]
