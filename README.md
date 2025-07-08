# Discord Speech-to-Write Bot

音声ファイルを Discord でアップロード ⇒ Whisper で文字起こし ⇒ GPT-4o-mini で要約 ⇒ Obsidian Vault へ保存／X 投稿文生成 までを自動化するボットです。

---

## クイックスタート
以下の **最短 3 ステップ** で動きます。（時間 5 分ほど）

### 1. ローカル実行
```bash
# 1) 依存関係インストール
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) .env を作成してキー入力
cp .env.example .env && vi .env  # 各種トークンを設定

# 3) 起動
python bot.py
```

### 2. Docker 実行
```bash
# 1) .env を用意（上と同じ）
# 2) ビルド
docker build -t discord-speech-bot .
# 3) 起動
docker run --rm --env-file .env discord-speech-bot
```

### 3. Railway デプロイ
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/vrJgJb?referralCode=xxxx)

1) 上記ボタンをクリック → GitHub リポジトリを選択  
2) Variables に `.env.example` の値をコピペ  
3) **Deploy** を押すと完成（ffmpeg も自動で入ります）

---

## ボットセットアップ (/setup コマンド)
サーバーにボットを招待後、管理者ロールで次のコマンドを実行します。
```text
/setup DISCORD_BOT_TOKEN=... OPENAI_API_KEY=... VAULT_PATH=...
```
これによりサーバー専用の設定が DB に保存され、以降は添付ファイルだけで動作します。

---

## 主要機能
- Whisper で文字起こし（自動拡張子変換）
- GPT-4o-mini で要約 & X 投稿文生成
- Obsidian Vault にマークダウン保存＋類似ノートリンク生成（Embeddings）

---

## ライセンス
MIT


1. .env を作成し、以下を設定  
DISCORD_TOKEN=... OPENAI_API_KEY=... VAULT_PATH=...

2. python bot.py で起動

※ この公開版には secrets は含めていません。
