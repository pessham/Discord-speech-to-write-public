# 音声文字おこし屋さん Bot 初心者向けマニュアル

> このドキュメントでは、**PC に不慣れな初心者**の方でも Discord Bot を自分のサーバーに導入し、音声文字起こし & 要約 Bot を使えるようになるまでを詳しく解説します。難しい単語には補足を付けていますので安心してください。

---

## 目次
1. [準備するもの](#準備するもの)
2. [Discord のインストール](#discord-のインストール)
3. [Discord サーバーを作成する](#discord-サーバーを作成する)
4. [Bot アプリを作成してトークンを取得](#bot-アプリを作成してトークンを取得)
5. [Bot をサーバーに招待する](#bot-をサーバーに招待する)
6. [PC 側の環境構築](#pc-側の環境構築)
7. [Bot のソースコードを取得](#bot-のソースコードを取得)
8. [設定ファイルを作る](#設定ファイルを作る)
9. [依存ライブラリをインストール](#依存ライブラリをインストール)
10. [Bot を起動する](#bot-を起動する)
11. [Bot の使い方](#bot-の使い方)
12. [アップデート方法](#アップデート方法)
13. [トラブルシューティング](#トラブルシューティング)

---

## 準備するもの
| 項目 | 説明 |
|------|------|
| **Discord アカウント** | すでに持っていれば OK。無ければ無料で作成します。 |
| **パソコン** | Windows 10/11 で確認済み。Mac でもほぼ同じ手順です。 |
| **Python 3.10 以上** | プログラミング言語。後ほどインストール手順を説明します。 |
| **Git** | ソースコードを取得するため。GUI クライアントでも OK。 |
| **ffmpeg** | 音声ファイルの変換に使用。 |
| **OpenAI API キー** | Whisper・ChatGPT を使うために必要（有料従量課金）。 |

---

## Discord のインストール
1. 公式サイト <https://discord.com/download> へアクセス。
2. Windows の場合は `Download for Windows` をクリックし、インストーラーを実行。
3. インストール完了後にアプリが起動するので、ログインまたはアカウントを新規作成します。

### スマホと PC の違いは？
Bot を動かすのは **PC 側** なので、スマホだけではセットアップできません。チャットの利用はスマホからでも OK です。

---

## Discord サーバーを作成する
1. Discord 左のサーバー一覧で `+` を押し `サーバーを作成` を選択。
2. テンプレートは空白で大丈夫です。名前を入力し `作成`。

> ここに自分専用 Bot を招待します。

---

## Bot アプリを作成してトークンを取得
1. ブラウザで Discord **Developer Portal** (<https://discord.com/developers/applications>) にアクセス。
2. `New Application` → アプリ名を入力 → `Create`。
3. 左メニュー **Bot** → `Add Bot` → `Yes, do it!`。
4. `Privileged Gateway Intents` の **MESSAGE CONTENT INTENT** と **SERVER MEMBERS INTENT** にチェックを入れて **Save**。
5. **Reset Token** → `Copy` でトークン（長い文字列）をメモ帳などに貼り付けて保存。
   *他人に見せると Bot を乗っ取られるので要注意！*

---

## Bot をサーバーに招待する
1. Developer Portal 左メニュー **OAuth2 → URL Generator** を開く。
2. `Scopes` で **bot** と **applications.commands** にチェック。
3. `Bot Permissions` で以下にチェック。
   - Send Messages
   - Embed Links
   - Read Message History
   - Add Reactions
4. ページ下に生成された URL をクリック → 先ほど作ったサーバーを選択 → **認証**。

> これでサーバーのメンバー一覧に Bot が追加されれば OK！

---

## PC 側の環境構築
### Python をインストール
1. 公式サイト <https://www.python.org/downloads/windows/> から **Python 3.11** など最新をダウンロード。
2. インストーラー起動時に **Add Python to PATH** に必ずチェックし **Install Now**。

### Git をインストール
1. <https://git-scm.com/download/win> からダウンロードし、デフォルト設定でインストール。

### ffmpeg をインストール
1. <https://www.gyan.dev/ffmpeg/builds/> → `git-full` ビルドをダウンロード。
2. zip を展開し、`ffmpeg/bin` フォルダーのパスを環境変数 `PATH` に追加。もしくは exe を bot フォルダーへコピー。

---

## Bot のソースコードを取得
```powershell
# 任意の作業フォルダーで
git clone https://github.com/your-account/Discord-speech-to-write-public.git
cd Discord-speech-to-write-public
```

---

## 設定ファイルを作る
1. `.env.example` をコピーして `.env` を作成。
2. 中身を編集し、`DISCORD_BOT_TOKEN` に先ほど取得したトークン、`OPENAI_API_KEY` に自分のキーを入力。
3. 保存。

---

## 依存ライブラリをインストール
```powershell
python -m venv .venv  # 仮想環境 (推奨)
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Bot を起動する
```powershell
python bot.py
```
コンソールに `Logged in as <Bot名>` と表示されれば成功。Discord アプリを見ると Bot がオンラインになります。

---

## Bot の使い方
### 基本
1. **stand.fm のエピソード URL** をチャットに貼る。
2. 直後に `👍` が付いたら準備完了。
3. 文字起こししてほしいときにチャットで **`もじ`** とだけ送信。
4. Bot が音声をダウンロード・文字起こしし、要約を返信してくれます。

### ファイル直接アップロード
1. 音声ファイル（mp3, wav, m4a など）を添付して `!transcribe` コマンドを送信。
2. Bot が文字起こしと要約を順番に返します。

### 管理者向けコマンド
| コマンド | 概要 |
|----------|------|
| `!setprompt <テキスト>` | 要約時のプロンプトをサーバー専用に設定 |
| `!showprompt` | 現在のプロンプトを表示 |
| `!post x|note` | **未実装**: 投稿テスト |

### 利用制限
- デフォルトで **1 サーバー 1 日 5 回** まで。超えるとプレミアムプランの案内メッセージが出ます。

---

## アップデート方法
```powershell
git pull  # 最新コードを取得
pip install -r requirements.txt --upgrade
```
変更があれば Bot を再起動してください。

---

## トラブルシューティング（オーナー／管理者向け）

| 症状 | 主な原因 | チェック & 解決方法 |
|------|-----------|------------------|
| Bot が **オフラインのまま** | • `.env` の `DISCORD_TOKEN` が誤り<br>• Bot トークンを再生成した | 1. Developer Portal → Bot → *Token* を再コピー<br>2. `.env` を更新して再起動
| コマンドや「もじ」に **無反応** | • `MESSAGE CONTENT INTENT` 未許可<br>• 権限 **Read Message History / Send Messages** 不足 | 1. Developer Portal → *Privileged Gateway Intents* を ON<br>2. サーバーのロールで上記権限を付与
| URL へ 👍 リアクションが付かない | • `Add Reactions` 権限不足<br>• メッセージが Bot の読めないチャンネル | 1. チャンネル権限に *Add Reactions* を追加<br>2. Bot がそのチャンネルを閲覧できるか確認
| `OpenAIAuthenticationError` や **API 鍵が無効** | `OPENAI_API_KEY` が失効 / 無料枠終了 | 1. OpenAI ダッシュボードで有効なキーを取得<br>2. `.env` 更新→再起動
| **Quota exceeded / 429 Too Many Requests** | OpenAI 月間/分間上限超過 | 1. Usage ページで残量確認<br>2. 上限引き上げ or 時間を置いて再実行
| 文字起こしが **途中で停止** する | • 音声が制限時間を超過<br>• ffmpeg 変換でエラー | 1. 20/60 分(プラン)以内か確認<br>2. `logs/bot.log` に ffmpeg 出力エラーが無いか確認
| `ffmpeg` が見つからない | OS に ffmpeg が未インストール / PATH 未設定 | • Windows: `choco install ffmpeg`<br>• macOS: `brew install ffmpeg`<br>• Linux: apt/yum でインストール後、`ffmpeg -version` が通るか確認
| `Missing Access` など権限系 Discord エラー | Bot ロール位置が低い / 権限不足 | サーバー設定 → ロール順序で Bot を上位へ移動し必要権限を確認
| `Cannot connect to host discord.com:443` | サーバー側のネットワーク or プロキシ | サーバーが外部に HTTPS 接続できるか (`curl https://discord.com`) を確認
| **自動更新がうまくいかない** | git pull で競合発生 | `git reset --hard origin/main` 後に `git pull` し、`pip install -r requirements.txt --upgrade` して再起動

> それでも解決しない場合は `logs/bot.log` を添付して GitHub Issue または Discord サポートサーバーへお問い合わせください。

---

## 参考リンク
- OpenAI Whisper API: <https://platform.openai.com/docs/guides/speech>
- Discord Developer Portal: <https://discord.com/developers>
- このプロジェクト GitHub: <https://github.com/your-account/Discord-speech-to-write-public>

---

> 不明点があれば Issue や Discord で気軽に質問してください！
