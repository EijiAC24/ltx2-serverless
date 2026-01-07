#!/bin/bash
# 不足しているDistilled LoRAをダウンロード

set -e

MODEL_DIR="/workspace/models"
cd $MODEL_DIR

echo "=== Downloading Distilled LoRA ==="

python3 << 'EOF'
from huggingface_hub import hf_hub_download

model_dir = "/workspace/models"

print("Downloading ltx-2-19b-distilled-lora-384.safetensors...")
hf_hub_download(
    repo_id="Lightricks/LTX-2",
    filename="ltx-2-19b-distilled-lora-384.safetensors",
    local_dir=model_dir
)

print("Done!")
EOF

echo ""
echo "=== Download Complete ==="
ls -lh /workspace/models/*.safetensors
