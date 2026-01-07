#!/bin/bash
# LTX-2 19B fp8 Setup Script for Runpod (RTX 4090)
# API Server版

set -e

echo "=== LTX-2 Setup Start ==="

cd /workspace

# uv インストール (高速パッケージマネージャー)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# LTX-2 リポジトリをクローン
if [ ! -d "LTX-2" ]; then
    git clone https://github.com/Lightricks/LTX-2.git
fi

cd LTX-2

# 依存関係インストール
uv sync --frozen
source .venv/bin/activate

# FastAPI 追加
pip install fastapi uvicorn python-multipart

# モデルディレクトリ作成
mkdir -p /workspace/models
mkdir -p /workspace/outputs

echo "=== Downloading Models ==="

# HuggingFace CLIでモデルダウンロード
pip install huggingface_hub

python3 << 'EOF'
from huggingface_hub import hf_hub_download, snapshot_download
import os

model_dir = "/workspace/models"

# LTX-2 fp8モデル
print("Downloading LTX-2 19B fp8...")
hf_hub_download(
    repo_id="Lightricks/LTX-2",
    filename="ltx-2-19b-dev-fp8.safetensors",
    local_dir=model_dir
)

# Spatial Upscaler (1080p出力用)
print("Downloading Spatial Upscaler...")
hf_hub_download(
    repo_id="Lightricks/LTX-2",
    filename="ltx-2-spatial-upscaler-x2-1.0.safetensors",
    local_dir=model_dir
)

# 設定ファイル
snapshot_download(
    repo_id="Lightricks/LTX-2",
    allow_patterns=["*.json", "*.txt", "*.yaml"],
    local_dir=model_dir
)

print("=== Model Download Complete ===")
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "APIサーバー起動:"
echo "  cd /workspace"
echo "  python server.py"
echo ""
echo "アクセス: http://<POD_IP>:8000"
echo "ドキュメント: http://<POD_IP>:8000/docs"
