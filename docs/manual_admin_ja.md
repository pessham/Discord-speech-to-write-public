# スタエフ文字おこし屋さん Bot 運用ガイド（サーバー管理者向け）

> このドキュメントは **Discord サーバーの管理者** として Bot を運用する際に必要な情報をまとめています。セットアップ済みの Bot をチームメンバーに快適に使ってもらうための設定、権限、トラブル対応方法などを記載しています。

---

## 1. Bot 招待後にまず行うこと
1. Bot ロールの位置を他の役職より上位に配置（絵文字リアクションやメッセージ閲覧権限が必要な場合）。
2. Bot に次の権限を付与:  
   - Send Messages  
   - Embed Links  
   - Read Message History  
   - Add Reactions  
3. `/server_settings → Integrations → Bot` でも権限を確認しておくと安心です。

---

## 2. 重要コマンド
| コマンド | 権限 | 用途 | 例 |
|----------|------|------|----|
| `!setprompt <テキスト>` | 管理者のみ | 要約プロンプトをサーバー専用に上書き | `!setprompt 関西弁で3行で要約してみて {text}` |
| `!showprompt` | 全員可 | 現在の要約プロンプトを表示 | `!showprompt` |
| `!post x|note` | 管理者のみ (未実装) | X / note への自動投稿テスト | `!post x` |
| `!transcribe` | 全員可 | 音声ファイル添付で文字起こし実行 | （ファイル添付） `!transcribe` |
| `もじ` | 全員可 | 直近 stand.fm URL に対して文字起こし & 要約 | `もじ` |

---

## 3. 日次利用制限（Quota）
- デフォルトで **1 サーバー 1 日 5 回** までです（`bot.py` の `_DAILY_LIMIT` 定数を変更可）。
- 制限を超えると `_LIMIT_MSG` の文言を Bot が送信します。
- OpenAI 利用料の管理目的で上限値を低めにしています。必要に応じて調整してください。

---

## 4. トークン・API キーのセキュリティ
- `DISCORD_BOT_TOKEN` と `OPENAI_API_KEY` は `.env` ファイルで管理し、**公開リポジトリには絶対に Push しない**。
- 共有する場合は 1Password などのシークレット共有ツールを利用。

---

## 5. Bot のアップデート手順
```bash
# 仮想環境を有効化後
git pull              # 最新ソース取得
pip install -r requirements.txt --upgrade
python bot.py         # 再起動
```
- Docker / Railway の場合は自動ビルド・再起動が走る設定にしておくと便利です。

---

## 6. よくあるトラブルと対応
| 症状 | 原因 | 対応 |
|------|------|------|
| 返信が 2 回届く | Bot プロセスが重複起動 | 片方を停止（クラウド + ローカル重複など） |
| `IndentationError` で起動失敗 | ソース編集時にインデント崩れ | `git pull` で最新に戻す or 該当行修正 |
| Bot がオフライン | `DISCORD_BOT_TOKEN` が誤り / Gateway Intents 無効 | トークン再発行 or Developer Portal で Intents 有効化 |
| 音声が処理されない | 音声が 20 分超 or ffmpeg 未設定 | 録音を短く & ffmpeg インストール確認 |
| OpenAI エラー (Rate limit / billing) | 無料枠や上限を超過 | OpenAI ダッシュボードで残高確認 & 課金設定 |

---

## 7. プロンプトのカスタマイズ例
```text
あなたは気さくなラジオ編集者です。
以下を 3 行でざっくり要約し、最後に作者が最も伝えたいメッセージを 1 行で書いてください。

{text}
```
- `{text}` プレースホルダを必ず含めてください。Bot が入力文に置換します。
- 口調変更: `ですます調`, `関西弁`, `若者言葉` など
- 出力形式を箇条書きにする、ハッシュタグを付ける等も可能です。

---

## 8. ログ監視
- `python bot.py` 実行時にコンソールへ INFO レベルでログが出ます。
- クラウド（Railway など）では Web コンソールの Logs タブで確認。
- `logging.basicConfig(level=logging.INFO, ...)` を変更して DEBUG 詳細ログも出せます。

---

### 連絡先
不明点や不具合があれば GitHub Issue または Discord で開発者にご連絡ください。
