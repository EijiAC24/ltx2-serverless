# LTX-2 API Server on Runpod Pods

RTX 4090 (24GB) で LTX-2 19B fp8 を API サーバーとして動かす

## 構成

| 項目 | 設定 |
|------|------|
| GPU | RTX 4090 (24GB) |
| モデル | LTX-2 19B fp8 |
| 解像度 | 1080p (1920x1080) |
| 動画長 | 最大15秒 |
| API | FastAPI |
| コスト | ~$0.69/hr |

## ファイル構成

```
Runpod/
├── setup.sh     # 初回セットアップ
├── server.py    # FastAPI サーバー
├── client.py    # API クライアント
└── README.md
```

---

## セットアップ手順

### 1. Pod 作成

1. [Runpod Pods](https://www.runpod.io/console/pods) へ
2. **+ Deploy** クリック
3. 設定:

| 項目 | 値 |
|------|-----|
| GPU | **RTX 4090** |
| Template | RunPod Pytorch 2.4.0 |
| Container Disk | 20GB |
| Volume Disk | **100GB** (モデル保存用) |
| Expose HTTP Ports | **8000** ← 重要！ |

4. **Deploy** クリック

### 2. 初回セットアップ（1回だけ）

Pod 起動後、Web Terminal または SSH で:

```bash
cd /workspace

# ファイルをアップロード or 直接作成
# setup.sh, server.py をアップロード

chmod +x setup.sh
./setup.sh
```

所要時間: 20-30分（モデルダウンロード含む）

### 3. API サーバー起動

```bash
cd /workspace/LTX-2
source .venv/bin/activate
cd /workspace
python server.py
```

起動後:
- API: `http://<POD_ID>-8000.proxy.runpod.net`
- ドキュメント: `http://<POD_ID>-8000.proxy.runpod.net/docs`

---

## API 使い方

### ヘルスチェック

```bash
curl http://<POD_URL>/health
```

### 動画生成（同期）

```bash
curl -X POST "http://<POD_URL>/generate/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cat walking in a garden, cinematic",
    "duration": 10,
    "width": 1920,
    "height": 1080
  }'
```

### 動画生成（非同期）

```bash
# ジョブ投入
curl -X POST "http://<POD_URL>/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A cat walking in a garden"}'

# ステータス確認
curl "http://<POD_URL>/status/<JOB_ID>"

# ダウンロード
curl "http://<POD_URL>/download/<JOB_ID>" -o video.mp4
```

### Python クライアント

```bash
# ヘルスチェック
python client.py --server http://<POD_URL> --health

# 動画生成
python client.py \
  --server http://<POD_URL> \
  --prompt "A cat walking in a garden" \
  --duration 10 \
  --output cat.mp4
```

---

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | サーバー情報 |
| GET | `/health` | ヘルスチェック |
| POST | `/generate` | 非同期生成 |
| POST | `/generate/sync` | 同期生成 |
| GET | `/status/{job_id}` | ジョブ状態 |
| GET | `/download/{job_id}` | 動画DL |
| GET | `/jobs` | ジョブ一覧 |
| GET | `/docs` | Swagger UI |

## リクエストパラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | - | 生成プロンプト |
| `negative_prompt` | string | - | "" | ネガティブ |
| `duration` | float | - | 10 | 秒数 (1-15) |
| `width` | int | - | 1920 | 幅 |
| `height` | int | - | 1080 | 高さ |
| `fps` | int | - | 24 | FPS |
| `seed` | int | - | null | シード |

---

## 運用

### Pod 停止（課金停止）

使わない時は Pod を **Stop** する
- Volume のデータは保持される
- 次回起動時はサーバー起動だけでOK

### 次回起動時

```bash
cd /workspace/LTX-2
source .venv/bin/activate
cd /workspace
python server.py
```

### バックグラウンド実行

```bash
nohup python server.py > server.log 2>&1 &
```

---

## コスト

| 項目 | コスト |
|------|--------|
| RTX 4090 | $0.69/hr |
| Volume 100GB | $0.07/GB/月 = $7/月 |
| 10秒動画1本 | ~30秒 = ~$0.006 |

### 月額目安（1日5本）

| 項目 | コスト |
|------|--------|
| GPU (30分/日 × 30日) | ~$10 |
| Volume | $7 |
| **合計** | **~$17/月** |

※ 実際は使い方次第。毎回停止すれば安くなる

---

## トラブルシューティング

### CUDA out of memory

解像度を下げる:
```json
{"width": 1280, "height": 720}
```

### ポートにアクセスできない

- Pod 作成時に HTTP Port 8000 を公開したか確認
- Proxy URL を使用: `https://<POD_ID>-8000.proxy.runpod.net`

### モデルロードが遅い

初回は時間かかる。2回目以降はキャッシュされて速い。
# Trigger rebuild
