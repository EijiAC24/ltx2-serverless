"""
Runpod Pod Manager
Pod の作成/終了/ステータス確認
"""

import os
import runpod

# 設定
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "your_api_key_here")
runpod.api_key = RUNPOD_API_KEY

# Pod設定 (RTX 6000 Ada)
POD_CONFIG = {
    "name": "ltx2-api",
    "image_name": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
    "gpu_type_id": "NVIDIA RTX 6000 Ada Generation",
    "cloud_type": "SECURE",
    "volume_in_gb": 0,  # Network Volume使用
    "container_disk_in_gb": 20,
    "ports": "8000/http",
    "volume_mount_path": "/workspace",
    "network_volume_id": "your_network_volume_id",  # Network Volume ID
}


def list_pods():
    """全Podを一覧表示"""
    pods = runpod.get_pods()
    print("=" * 60)
    print("PODS")
    print("=" * 60)
    for pod in pods:
        status = pod.get("desiredStatus", "unknown")
        gpu = pod.get("machine", {}).get("gpuDisplayName", "N/A")
        print(f"ID: {pod['id']}")
        print(f"  Name: {pod.get('name', 'N/A')}")
        print(f"  Status: {status}")
        print(f"  GPU: {gpu}")
        print("-" * 40)
    return pods


def get_pod(pod_id: str):
    """Pod詳細を取得"""
    pod = runpod.get_pod(pod_id)
    return pod


def terminate_pod(pod_id: str):
    """Podを終了（削除）"""
    print(f"Terminating pod: {pod_id}")
    result = runpod.terminate_pod(pod_id)
    print("Pod terminated")
    return result


def create_pod():
    """新しいPodを作成"""
    print("Creating new pod...")
    print(f"Config: {POD_CONFIG}")

    pod = runpod.create_pod(**POD_CONFIG)
    print(f"Pod created: {pod['id']}")
    return pod


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Runpod Pod Manager")
    parser.add_argument("--list", action="store_true", help="List all pods")
    parser.add_argument("--get", type=str, help="Get pod details by ID")
    parser.add_argument("--terminate", type=str, help="Terminate pod by ID")
    parser.add_argument("--create", action="store_true", help="Create new pod")

    args = parser.parse_args()

    if args.list:
        list_pods()
    elif args.get:
        pod = get_pod(args.get)
        print(pod)
    elif args.terminate:
        terminate_pod(args.terminate)
    elif args.create:
        create_pod()
    else:
        parser.print_help()
