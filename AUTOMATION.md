# LTX-2 動画自動生成・配信システム

## 概要

| コンポーネント | サービス | 用途 |
|--------------|---------|------|
| プロンプト生成 | Grok API | AIでプロンプト自動生成 |
| データ管理 | Google Sheets | プロンプト・ステータス管理 |
| 動画生成 | Runpod Serverless (LTX-2) | 動画生成 |
| 配信 | Later API | SNS配信スケジュール |
| 実行環境 | GitHub Actions | 毎日定時実行 |

---

## フロー図

```
┌─────────────────────────────────────────────────────────────────┐
│              GitHub Actions - Daily Automation                   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  ┌──────────┐         ┌──────────────┐      ┌──────────────┐
  │  Grok    │────────▶│ Google       │─────▶│  Runpod      │
  │  API     │         │ Sheets       │      │  LTX-2       │
  └──────────┘         └──────────────┘      └──────────────┘
       │                      │                     │
       │ プロンプト生成        │ 保存・管理           │ 動画生成
       │                      │                     │
       └──────────────────────┼─────────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  Later API   │
                       │  (配信)      │
                       └──────────────┘
```

---

## クイックスタート

### 1. リポジトリをGitHubにプッシュ

```bash
cd C:\Users\Eiji\Documents\Apps\AVmodel\Runpod
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/ltx2-automation.git
git push -u origin main
```

### 2. GitHub Secrets 設定

Settings → Secrets and variables → Actions → New repository secret

| Secret Name | 説明 |
|-------------|------|
| `GROK_API_KEY` | Grok API キー |
| `RUNPOD_API_KEY` | Runpod API キー |
| `GOOGLE_CREDENTIALS_JSON` | Service Account JSON (全体) |
| `SPREADSHEET_ID` | Google Sheets ID |
| `LATER_API_KEY` | Later API キー |
| `LATER_PROFILE_ID` | Later プロフィール ID |

### 3. Google Sheets セットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. Google Sheets API を有効化
3. Service Account 作成 → JSON キー発行
4. スプレッドシート作成 → Service Account メールに編集権限付与
5. JSON を `GOOGLE_CREDENTIALS_JSON` Secret に保存

### 4. 手動実行テスト

Actions → Daily Automation → Run workflow

---

## 詳細フロー

### Phase 1: プロンプト生成

```
1. Grok API呼び出し
   └─▶ カテゴリ: cute animals, vintage, nature, comedic
   └─▶ 各カテゴリ 1-2 プロンプト生成

2. Google Sheetsに保存
   └─▶ 新規行として追加
   └─▶ ステータス: "pending"
```

### Phase 2: 動画生成

```
1. Sheetsから "pending" のプロンプト取得
   └─▶ 1日5本に制限

2. Runpod API でジョブ投入
   └─▶ 576x1024, 10秒, 20ステップ
   └─▶ ステータス: "generating"

3. 完了待ち
   └─▶ ステータス: "generated"
   └─▶ job_id, cost 記録
```

### Phase 3: 配信スケジュール

```
1. Sheetsから "generated" の動画取得

2. Later APIで配信予約
   └─▶ 翌日9:00から2時間おきに配信
   └─▶ ステータス: "scheduled"
```

---

## ファイル構成

```
Runpod/
├── .github/
│   └── workflows/
│       └── daily-automation.yml  # GitHub Actions 定義
├── automation/
│   ├── __init__.py
│   ├── config.py           # 環境変数から設定読み込み
│   ├── grok_client.py      # Grok API クライアント
│   ├── sheets_client.py    # Google Sheets クライアント
│   ├── ltx_client.py       # Runpod LTX-2 クライアント
│   ├── later_client.py     # Later API クライアント
│   ├── daily_run.py        # 統合スクリプト
│   └── requirements.txt    # Python依存関係
├── AUTOMATION.md           # このドキュメント
├── USAGE.md                # LTX-2 使い方ガイド
├── handler.py              # Serverless ハンドラー
└── Dockerfile
```

---

## Google Sheets 構造

| 列 | フィールド | 説明 |
|----|-----------|------|
| A | id | ユニークID |
| B | created_at | 作成日時 |
| C | prompt | 生成プロンプト |
| D | category | カテゴリ |
| E | status | pending/generating/generated/scheduled/published/error |
| F | job_id | Runpod Job ID |
| G | video_url | 動画参照 (job:xxx) |
| H | duration | 動画長 (秒) |
| I | resolution | 解像度 |
| J | cost | 生成コスト ($) |
| K | scheduled_at | 配信予定日時 |
| L | published_at | 配信完了日時 |
| M | later_id | Later Post ID |
| N | caption | SNSキャプション |
| O | hashtags | ハッシュタグ (カンマ区切り) |
| P | error | エラーメッセージ |

---

## GitHub Actions

### 定期実行

```yaml
schedule:
  - cron: '0 6 * * *'  # 毎日 6:00 UTC (15:00 JST)
```

### 手動実行オプション

| オプション | 説明 |
|-----------|------|
| `all` | 全Phase実行 (デフォルト) |
| `prompts` | Phase 1 のみ |
| `videos` | Phase 2 のみ |
| `schedule` | Phase 3 のみ |

### コマンドライン

```bash
# 全Phase実行
python automation/daily_run.py

# 個別実行
python automation/daily_run.py --prompts
python automation/daily_run.py --videos
python automation/daily_run.py --schedule

# 数量指定
python automation/daily_run.py --videos --count 3
```

---

## コスト見積もり

### 動画生成 (Runpod)

| 項目 | 単価 | 日5本 | 月150本 |
|------|------|-------|---------|
| 576x1024, 10秒 | $0.16 | $0.80 | ~$24 |

### API費用

| サービス | 見積もり |
|---------|---------|
| Grok API | ~$5-10/月 |
| Google Sheets API | 無料 |
| GitHub Actions | 無料 (2000分/月) |
| Later API | プラン次第 |

### 合計目安

```
$24 (動画) + $10 (Grok) + Later = ~$35-50/月 + Later費用
```

---

## トラブルシューティング

### Grok API エラー

```
Error: 401 Unauthorized
```
→ `GROK_API_KEY` が正しいか確認

### Google Sheets エラー

```
Error: 403 Forbidden
```
→ Service Account にスプレッドシートの編集権限があるか確認

### Runpod タイムアウト

```
TimeoutError: Job xxx timed out
```
→ 高解像度は時間がかかる。`MAX_POLL_TIME` を増やす

### Later API エラー

Later API の仕様に合わせて `later_client.py` を調整する必要あり

---

## セットアップチェックリスト

- [ ] GitHub リポジトリ作成
- [ ] Secrets 設定
  - [ ] `GROK_API_KEY`
  - [ ] `RUNPOD_API_KEY`
  - [ ] `GOOGLE_CREDENTIALS_JSON`
  - [ ] `SPREADSHEET_ID`
  - [ ] `LATER_API_KEY`
  - [ ] `LATER_PROFILE_ID`
- [ ] Google Sheets
  - [ ] Service Account 作成
  - [ ] Sheets API 有効化
  - [ ] スプレッドシート作成 & 権限付与
- [ ] Later API
  - [ ] アカウント作成
  - [ ] API キー取得
  - [ ] プロフィール ID 確認
- [ ] テスト実行
  - [ ] 手動ワークフロー実行
  - [ ] ログ確認

---

## 注意事項

### プロンプトのコツ (USAGE.md 参照)

- `negative_prompt` は使わない
- `"no text"` は書かない（逆効果）
- 解像度は64の倍数
- 日本語地名は避ける（テキストが出る）

### セキュリティ

- API キーは必ず Secrets に保存
- `GOOGLE_CREDENTIALS_JSON` は JSON 全体を保存
- リポジトリを Public にする場合は Secrets が漏れないよう注意

### コスト管理

- `DAILY_VIDEO_COUNT` で日次上限設定 (デフォルト: 5)
- 月額が増えたら解像度を下げる or 本数を減らす
