# LTX-2 Serverless 使い方ガイド

## 概要

| 項目 | 値 |
|------|-----|
| モデル | LTX-2 19B fp8 |
| GPU | RTX 6000 Ada (48GB) |
| Endpoint ID | `j01yykel5de361` |
| コスト | ~$0.00106/秒 |

---

## API エンドポイント

```
https://api.runpod.ai/v2/j01yykel5de361/run
```

### 認証

```
Authorization: Bearer <RUNPOD_API_KEY>
```

---

## 基本的な使い方

### 1. ジョブ投入

```bash
curl -X POST "https://api.runpod.ai/v2/j01yykel5de361/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "A cat walking in a garden",
      "duration": 10,
      "width": 576,
      "height": 1024,
      "steps": 20
    }
  }'
```

**レスポンス**:
```json
{"id": "xxx-xxx-xxx", "status": "IN_QUEUE"}
```

### 2. ステータス確認

```bash
curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
  "https://api.runpod.ai/v2/j01yykel5de361/status/<JOB_ID>"
```

### 3. 動画取得

完了後、レスポンスの `output.video_base64` をデコード:

```python
import base64
import json

data = json.loads(response)
video_bytes = base64.b64decode(data["output"]["video_base64"])
with open("output.mp4", "wb") as f:
    f.write(video_bytes)
```

---

## パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | - | 生成プロンプト |
| `duration` | float | - | 3 | 動画の長さ (秒) |
| `width` | int | - | 1280 | 幅 (64の倍数) |
| `height` | int | - | 768 | 高さ (64の倍数) |
| `steps` | int | - | 8 | 推論ステップ数 (20推奨) |
| `seed` | int | - | null | シード値 |

### ⚠️ negative_prompt は使わない

公式ガイドにネガティブプロンプトの記載なし。使用すると逆効果の可能性あり。

### 解像度の注意

**width と height は64の倍数が必須！**

| アスペクト比 | 推奨解像度 | 用途 |
|-------------|-----------|------|
| 9:16 (縦) | 576x1024 | リール/TikTok |
| 9:16 (縦HD) | 1088x1920 | 高品質リール |
| 16:9 (横) | 1280x768 | YouTube |
| 1:1 (正方形) | 1024x1024 | Instagram |

---

## プロンプトのコツ

[LTX-2 Prompting Guide](https://ltx.io/model/model-blog/prompting-guide-for-ltx-2) 参照

### 良いプロンプトの構成

1. **ショット設定** - カメラアングル、構図 (close-up, medium shot, wide shot)
2. **シーン設定** - 照明、色調、雰囲気
3. **アクション** - 動きの流れを自然に記述 (現在形で)
4. **キャラクター** - 外見、服装、表情
5. **カメラワーク** - パン、ズーム、手持ち風など
6. **音声/セリフ** - 引用符で囲む、アクセント指定

### セリフの書き方

LTX-2は音声生成可能！

```
speaking in enthusiastic English, "Oh my god this is amazing!"
speaking in a deadpan British accent, "I know what you did."
speaking in Japanese, "すごい！たのしい！"
```

### ⚠️ 避けるべきこと

| NG | 理由 |
|----|------|
| `no text`, `no subtitles` | 逆にテキストを連想させる |
| 感情ラベル (`sad`, `happy`) | 表情・姿勢で表現すべき |
| 複雑な物理演算 | ジャンプ、ジャグリング等は苦手 |
| シーン詰め込みすぎ | 1-2アクションに絞る |
| 複数キャラ多すぎ | シンプルに |

### 良い例

```
Close-up of an orange tabby cat sitting on a modern kitchen
counter in warm morning sunlight. The cat stares directly
into camera with an intense judgmental expression and speaks
in a deadpan British accent, "I know what you did last night."
The cat slowly blinks with smug satisfaction. The camera slowly
pushes in on the cat's face. Shallow depth of field, cinematic
lighting, comedic tone.
```

### ヴィンテージ映像の例

```
Old monochrome documentary film footage from the 1920s with
heavy film grain, scratches, and flickering. A young man in
traditional Edo period kimono wearing handcrafted wooden goggles
sits on tatami floor. He waves his hands excitedly, speaking in
English, "This is incredible! I can see another world!"
Authentic vintage film aesthetic, sepia tones.
```

---

## 推奨設定

### コスパ重視 (推奨)

```json
{
  "prompt": "...",
  "duration": 10,
  "width": 576,
  "height": 1024,
  "steps": 20
}
```
- 生成時間: ~2.5分
- コスト: ~$0.16

### 高品質

```json
{
  "prompt": "...",
  "duration": 10,
  "width": 1088,
  "height": 1920,
  "steps": 20
}
```
- 生成時間: ~9分
- コスト: ~$0.57

---

## コスト計算

**$0.00106/秒** (計算時間)

| 解像度 | 秒数 | 生成時間 | コスト |
|--------|------|----------|--------|
| 576x1024 | 10秒 | ~150秒 | ~$0.16 |
| 1088x1920 | 10秒 | ~540秒 | ~$0.57 |

### 月額目安

| 使用量 | コスト |
|--------|--------|
| 10本/日 (576x1024) | ~$48/月 |
| 5本/日 (576x1024) | ~$24/月 |

### 公式API比較

| サービス | 10秒動画 |
|---------|----------|
| 公式 LTX API | $0.40〜$0.60 |
| Runpod Serverless | ~$0.16 |

**Runpodの方が60-75%安い**

---

## Python クライアント例

```python
import requests
import base64
import time

API_KEY = "your_api_key"
ENDPOINT = "https://api.runpod.ai/v2/j01yykel5de361"

def generate_video(prompt, duration=10, width=576, height=1024, steps=20):
    # ジョブ投入
    response = requests.post(
        f"{ENDPOINT}/run",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "input": {
                "prompt": prompt,
                "duration": duration,
                "width": width,
                "height": height,
                "steps": steps
            }
        }
    )
    job_id = response.json()["id"]
    print(f"Job submitted: {job_id}")

    # 完了待ち
    while True:
        status = requests.get(
            f"{ENDPOINT}/status/{job_id}",
            headers={"Authorization": f"Bearer {API_KEY}"}
        ).json()

        if status["status"] == "COMPLETED":
            video_b64 = status["output"]["video_base64"]
            return base64.b64decode(video_b64)
        elif status["status"] == "FAILED":
            raise Exception(status.get("error"))

        time.sleep(10)

# 使用例
video = generate_video("A cat walking in a garden, cinematic lighting")
with open("output.mp4", "wb") as f:
    f.write(video)
```

---

## ヘルスチェック

```bash
curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
  "https://api.runpod.ai/v2/j01yykel5de361/health"
```

---

## トラブルシューティング

### 解像度エラー

```
ValueError: Resolution is not divisible by 64
```
→ width/height を64の倍数に修正

### テキスト/字幕が出る

- `no text` 等を書かない（逆効果）
- 場所名（Tokyo等）を避ける
- シンプルなシーンを選ぶ

### タイムアウト

長時間動画や高解像度は時間がかかる。ポーリング間隔を長めに。

### ワーカー起動待ち

アイドル状態から起動に30-60秒かかる場合あり。
