#!/bin/bash
# Network Volume にモデルをダウンロードするスクリプト
# Pod起動後に1回だけ実行

set -e

echo "=== LTX-2 Model Download ==="

# Network Volume のパス
VOLUME_PATH="/runpod-volume"
MODEL_DIR="${VOLUME_PATH}/models"

mkdir -p ${MODEL_DIR}

# pip インストール
pip install huggingface_hub

# モデルダウンロード
python3 << 'EOF'
from huggingface_hub import hf_hub_download
import os

model_dir = "/runpod-volume/models"

print("Downloading LTX-2 19B fp8...")
hf_hub_download(
    repo_id="Lightricks/LTX-2",
    filename="ltx-2-19b-dev-fp8.safetensors",
    local_dir=model_dir
)

print("Downloading Spatial Upscaler...")
hf_hub_download(
    repo_id="Lightricks/LTX-2",
    filename="ltx-2-spatial-upscaler-x2-1.0.safetensors",
    local_dir=model_dir
)

print("Downloading config files...")
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Lightricks/LTX-2",
    allow_patterns=["*.json", "*.txt", "*.yaml"],
    local_dir=model_dir
)

print("=== Download Complete ===")
print(f"Models saved to: {model_dir}")

# 確認
import os
for f in os.listdir(model_dir):
    size = os.path.getsize(os.path.join(model_dir, f)) / (1024**3)
    print(f"  {f}: {size:.2f} GB")
EOF

echo ""
echo "Done! モデルが ${MODEL_DIR} に保存されました"
echo "このPodは停止してOKです"
