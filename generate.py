#!/usr/bin/env python3
"""
LTX-2 19B fp8 動画生成スクリプト
RTX 4090 (24GB) / 1080p / 10秒動画用
"""

import argparse
import os
import torch
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="LTX-2 Video Generation")
    parser.add_argument("--prompt", type=str, required=True, help="動画生成プロンプト")
    parser.add_argument("--negative_prompt", type=str, default="", help="ネガティブプロンプト")
    parser.add_argument("--output", type=str, default="output.mp4", help="出力ファイル名")
    parser.add_argument("--duration", type=float, default=10.0, help="動画の長さ(秒)")
    parser.add_argument("--width", type=int, default=1920, help="出力幅")
    parser.add_argument("--height", type=int, default=1080, help="出力高さ")
    parser.add_argument("--fps", type=int, default=24, help="フレームレート")
    parser.add_argument("--seed", type=int, default=None, help="シード値")
    parser.add_argument("--model_dir", type=str, default="/workspace/models/ltx2", help="モデルディレクトリ")
    args = parser.parse_args()

    print(f"=== LTX-2 Video Generation ===")
    print(f"Prompt: {args.prompt}")
    print(f"Output: {args.output}")
    print(f"Duration: {args.duration}s @ {args.fps}fps")
    print(f"Resolution: {args.width}x{args.height}")
    print()

    # フレーム数計算 (8+1の倍数に調整)
    num_frames = int(args.duration * args.fps)
    num_frames = ((num_frames - 1) // 8) * 8 + 1  # 8+1の倍数に
    print(f"Frames: {num_frames}")

    # シード設定
    if args.seed is not None:
        torch.manual_seed(args.seed)
        print(f"Seed: {args.seed}")

    # LTX-2パイプライン読み込み
    try:
        from ltx_pipelines import TI2VidTwoStagesPipeline

        print("Loading LTX-2 fp8 model...")
        pipe = TI2VidTwoStagesPipeline.from_pretrained(
            args.model_dir,
            torch_dtype=torch.bfloat16,
            fp8transformer=True,  # fp8有効化
        )
        pipe.to("cuda")

        # メモリ最適化
        pipe.enable_xformers_memory_efficient_attention()

    except ImportError:
        print("ltx_pipelinesが見つかりません。")
        print("代替方法: CLIを使用してください")
        print()
        print("CLI例:")
        print(f'  python -m ltx_pipelines.generate \\')
        print(f'    --prompt "{args.prompt}" \\')
        print(f'    --num_frames {num_frames} \\')
        print(f'    --width {args.width} --height {args.height} \\')
        print(f'    --output {args.output} \\')
        print(f'    --fp8transformer')
        return

    print("Generating video...")

    # 動画生成
    output = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        num_frames=num_frames,
        width=args.width,
        height=args.height,
        num_inference_steps=50,
        guidance_scale=7.5,
    )

    # 保存
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output.save(str(output_path))
    print(f"Saved: {output_path}")
    print("Done!")

if __name__ == "__main__":
    main()
