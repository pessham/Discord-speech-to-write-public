# スタエフ文字おこし屋さん Bot 初心者向けマニュアル

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

## トラブルシューティング
| 症状 | 原因と対処 |
|------|-----------|
| `IndentationError` など Python のエラーが出て起動しない | 途中でコードを編集してインデントが崩れた可能性があります。最新のリポジトリを取得し直すか、エラー行付近を確認。 |
| Bot がオフライン表示のまま | `.env` のトークンが間違っている、または `MESSAGE CONTENT INTENT` を有効にしていない。 |
| 文字起こしが途中で止まる | 音声が 20 分を超えていないか、OpenAI API の利用上限を超えていないか確認。 |
| `ffmpeg` が見つからないと言われる | PATH が通っていない。`ffmpeg -version` がコマンドプロンプトで動くか確認。 |

---

## 参考リンク
- OpenAI Whisper API: <https://platform.openai.com/docs/guides/speech>
- Discord Developer Portal: <https://discord.com/developers>
- このプロジェクト GitHub: <https://github.com/your-account/Discord-speech-to-write-public>

---

> 不明点があれば Issue や Discord で気軽に質問してください！
