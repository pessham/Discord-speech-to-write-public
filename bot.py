import logging, sys, os
from pathlib import Path
from utils.speech import transcribe as whisper_transcribe

from config import DISCORD_BOT_TOKEN, VAULT_PATH

import discord
from discord import File, Interaction
from discord.ext import commands

from utils.speech import transcribe, _convert_to_mp3
from utils.summarize import summarize


import re, asyncio, os, tempfile, subprocess, httpx, json
from pydub import AudioSegment
import json as _json
from openai import OpenAI
from datetime import date

# stand.fm episode URL (allow uppercase and query string)
STANDFM_RE = re.compile(r'https?://stand\.fm/episodes/[0-9A-Fa-f]+(?:[^\s]*)?')
# no keyword triggers, use two-step flow
pending_urls: dict[int, str] = {}  # channel_id -> url
# Default limit for audio length (seconds) for free servers
MAX_SECONDS = 20 * 60  # 20 minutes
openai_client = OpenAI()

# --- Daily quota control ----------------------------------------------------
_DAILY_LIMIT = 5
_LIMIT_MSG = (
    "残念！スタンダードプランでは1日5回までです。"
    "6回以上使いたい場合は月5$のプレミアムプランに入っていいかオーナーさんにおねだりしてみてね！ https://pessham.com/stmoji/"
)

# guild_id -> (date, count)
_daily_usage: dict[int, tuple[date, int]] = {}

# --- Premium / paid servers -------------------------------------------------
# Comma-separated guild IDs via env var e.g. "12345,67890"
_PREMIUM_GUILD_IDS: set[int] = {int(x) for x in os.getenv("PREMIUM_GUILD_IDS", "").split(",") if x.strip().isdigit()}

def _is_premium(guild_id: int) -> bool:
    return guild_id in _PREMIUM_GUILD_IDS

# --- Per-guild prompt templates -------------------------------------------
_PROMPT_FILE = Path("prompts.json")
DEFAULT_PROMPT = (
    "あなたは気さくなラジオ編集者です。\n"
    "以下を 3 行でざっくり要約し、最後に作者が最も伝えたいであろうメッセージを 1 行で書いてください。\n\n{text}"
)
DEFAULT_FILE_PROMPT = (
    "次の日本語テキストを読み、100文字程度で内容要約を1つ作成してください。その後、以下のSNS投稿テンプレートに従ってX(Twitter)用投稿文を作成してください。note用出力は不要です。\n"
    "\n【テンプレート】\n"
    "1. 読者への問い掛けや断定\n"
    "2. 重要ポイント箇条書き(2~3行)\n"
    "3. 筆者の体験談1行\n"
    "4. 主張を強める or エモい一言\n"
    "5. 行動を促す呼び掛け\n"
    "\n制約:\n- フレンドリーで信頼感のある語り口\n- 行動を促す言葉を含める\n- 体験談でリアルさを出す\n- テンポよく140字以内\n"
    "\n--- 入力テキスト ---\n{text}\n--------------------"
)
_prompt_map: dict[int, str] = {}  # スタンドFM URL用プロンプト
_file_prompt_map: dict[int, str] = {}  # ファイルアップロード用プロンプト
if _PROMPT_FILE.exists():
    try:
        data = json.loads(_PROMPT_FILE.read_text(encoding="utf-8"))
        _prompt_map.update(data.get("standfm", {}))
        _file_prompt_map.update(data.get("file", {}))
    except Exception as e:
        logging.warning("Failed to load prompts.json: %s", e)

def _save_prompts():
    try:
        data = {
            "standfm": _prompt_map,
            "file": _file_prompt_map
        }
        _PROMPT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logging.warning("Failed to save prompts.json: %s", e)

def _check_quota(guild_id: int) -> bool:
    """Return True if the guild has remaining quota for today."""
    today = date.today()
    stored = _daily_usage.get(guild_id)
    if stored is None or stored[0] != today:
        _daily_usage[guild_id] = (today, 0)
        stored = _daily_usage[guild_id]
    _, count = stored
    if _is_premium(guild_id):
        return True  # unlimited for premium guilds
    if count >= _DAILY_LIMIT:
        return False
    _daily_usage[guild_id] = (today, count + 1)
    return True

def _get_duration_sec(path: str) -> float:
    """Return audio duration in seconds using ffprobe (avoids loading whole file)."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = _json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0

async def _yt_download(url: str, dst: str) -> tuple[bool, str]:
    """Download audio. Return (success, error_message)."""
    try:
        # 最初の試行：標準的なダウンロード
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "-f", "bestaudio", "-o", dst, url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return True, ""
        
        # エラー内容を解析
        error_text = stderr.decode('utf-8', errors='ignore')
        logging.warning(f"yt-dlp failed for {url}: {error_text}")
        
        # 1秒待ってから再試行（一時的な問題の可能性）
        await asyncio.sleep(1)
        
        # 再試行：より多くのフォーマットを試す
        proc2 = await asyncio.create_subprocess_exec(
            "yt-dlp", "-f", "best[height<=720]/best", "--no-check-certificate", "-o", dst, url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout2, stderr2 = await proc2.communicate()
        
        if proc2.returncode == 0:
            logging.info(f"yt-dlp succeeded on retry for {url}")
            return True, ""
        
        # 両方失敗した場合、詳細なエラー情報を返す
        error_text2 = stderr2.decode('utf-8', errors='ignore')
        logging.error(f"yt-dlp failed twice for {url}: {error_text2}")
        
        # エラータイプを判定
        combined_error = error_text + " " + error_text2
        if "private" in combined_error.lower() or "members" in combined_error.lower():
            return False, "メンバーシップ限定"
        elif "not available" in combined_error.lower():
            return False, "配信が見つからない"
        elif "region" in combined_error.lower():
            return False, "地域制限"
        elif "403" in combined_error or "forbidden" in combined_error.lower():
            return False, "アクセス拒否"
        elif "network" in combined_error.lower() or "connection" in combined_error.lower():
            return False, "ネットワークエラー"
        else:
            return False, f"未知のエラー: {error_text[:100]}"
    
    except Exception as e:
        logging.exception(f"Exception in _yt_download: {e}")
        return False, f"システムエラー: {str(e)}"


def _trim(src: str, dst: str):
    audio = AudioSegment.from_file(src)
    audio[: MAX_SECONDS * 1000].export(dst, format="mp3")


async def _whisper(path: str) -> str:
    """Transcribe audio using utils.speech which converts to 24kbps MP3 before upload."""
    return await asyncio.to_thread(whisper_transcribe, Path(path))


async def _summarize(text: str, guild_id: int) -> str:
    """スタンドFM URL用の要約（旧形式）"""
    tmpl = _prompt_map.get(guild_id, DEFAULT_PROMPT)
    prompt = tmpl.format(text=text)
    def _do() -> str:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    return await asyncio.to_thread(_do)

async def _summarize_file(text: str, guild_id: int) -> dict:
    """ファイルアップロード用の要約（新形式）"""
    tmpl = _file_prompt_map.get(guild_id, DEFAULT_FILE_PROMPT)
    prompt = tmpl.format(text=text)
    def _do() -> dict:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        parts = content.split("\n", 1)  # first line summary, rest X tweet
        return {
            "summary": parts[0].strip(),
            "x": parts[1].strip() if len(parts) > 1 else "",
        }
    return await asyncio.to_thread(_do)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,  # Ensure logs go to stdout so Railway doesn't mark them as error
    force=True,
)

# Load credentials from .env (handled by python-dotenv in config.py)
TOKEN = DISCORD_BOT_TOKEN
if TOKEN is None:
    raise RuntimeError("DISCORD_BOT_TOKEN must be set in .env")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


audio_extensions = {".wav", ".mp3", ".m4a", ".ogg", ".oga", ".webm"}


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")


async def _process_attachment(channel, attachment, original_author):
    if Path(attachment.filename).suffix.lower() not in audio_extensions:
        return False
    tmp = Path("temp"); tmp.mkdir(exist_ok=True)
    file_path = tmp / attachment.filename
    await attachment.save(file_path)

    # 音声の長さをチェックする
    dur = _get_duration_sec(str(file_path))
    limit = 60 * 60 if _is_premium(channel.guild.id) else MAX_SECONDS
    if dur > limit:
        if _is_premium(channel.guild.id):
            await channel.send("僕は60分を超える放送の文字おこしは出来ないよ！60分以内の放送をアップしてね！")
        else:
            await channel.send("僕は20分を超える放送の文字おこしは出来ないよ！20分以内の放送をアップしてね！")
        return True # 処理済みとしてTrueを返す

    await channel.send("文字起こし中…")
    transcript = await asyncio.to_thread(transcribe, file_path)
    await channel.send("要約中…")
    # ファイルアップロード用プロンプトを使用
    parts = await _summarize_file(transcript, channel.guild.id)
    # separate messages
    await channel.send(transcript)
    await channel.send(f"{parts['summary']}\n\n{parts['x']}")
    return True

@bot.command(name="transcribe")
async def _transcribe(ctx: commands.Context):
    if not ctx.message.attachments:
        await ctx.send("音声ファイルを添付してください。")
        return
    await _process_attachment(ctx, ctx.message.attachments[0], ctx.author)


@bot.event
async def on_message(message: discord.Message):
    logging.info("recv: %s", message.content)
    # Ignore own bot messages
    if message.author.bot:
        return

    content = message.content

    # --- stand.fm URL storage -------------------------------------------------
    m = STANDFM_RE.search(content)
    if m:
        pending_urls[message.channel.id] = m.group(0)
        try:
            await message.add_reaction("👍")
        except discord.Forbidden:
            logging.warning("Missing permission to add reactions in this channel.")
        return

    # --- Trigger by exact 'もじ' ---------------------------------------------
    if content.strip() == "もじ":
        url = pending_urls.get(message.channel.id)
        if not url:
            await message.reply("先に stand.fm のエピソード URL を送ってください。", mention_author=False)
            return
        if not _check_quota(message.guild.id):
            await message.reply(_LIMIT_MSG, mention_author=False)
            return
        await message.channel.typing()
        with tempfile.TemporaryDirectory() as td:
            raw = os.path.join(td, "raw.m4a")
            success, error_msg = await _yt_download(url, raw)
            if not success:
                # エラータイプに応じたメッセージ
                if error_msg == "メンバーシップ限定":
                    await message.reply("僕はメンバーシップなど公開されていない放送の文字おこしは出来ないよ！誰でも聴くことが出来る放送をアップしてね！", mention_author=False)
                elif error_msg == "配信が見つからない":
                    await message.reply("このスタンドFM URLの配信が見つからないよ！URLが正しいか確認してね！", mention_author=False)
                elif error_msg == "地域制限":
                    await message.reply("この配信は地域制限がかかっているみたい！日本国内からアクセス可能な配信をアップしてね！", mention_author=False)
                elif error_msg == "アクセス拒否":
                    await message.reply("スタンドFMからのアクセスが拒否されました。しばらく時間を置いてから再試行してね！", mention_author=False)
                elif error_msg == "ネットワークエラー":
                    await message.reply("ネットワークエラーが発生しました。しばらく時間を置いてから再試行してね！", mention_author=False)
                else:
                    await message.reply(f"音声のダウンロードに失敗しました。エラー詳細: {error_msg}\n\nしばらく時間を置いてから再試行するか、別の配信URLを試してね！", mention_author=False)
                return

            dur = _get_duration_sec(raw)
            limit = 60 * 60 if _is_premium(message.guild.id) else MAX_SECONDS
            if dur > limit:
                if _is_premium(message.guild.id):
                    await message.reply("僕は60分を超える放送の文字おこしは出来ないよ！60分以内の放送をアップしてね！", mention_author=False)
                else:
                    await message.reply("僕は20分を超える放送の文字おこしは出来ないよ！20分以内の放送をアップしてね！", mention_author=False)
                return

            logging.info("yt-dlp done, duration=%.1fs", dur)
            # --- Long transcription with heartbeat to avoid idle shutdown ---
            logging.info("start whisper upload, size=%.1fMB", Path(raw).stat().st_size / 1e6)
            await message.channel.send("🎧 文字起こし中…（数分かかります）")
            try:
                whisper_task = asyncio.create_task(_whisper(raw))
                while not whisper_task.done():
                    logging.info("still working…")
                    await asyncio.sleep(10)
                text = await whisper_task
                logging.info("whisper length=%d chars", len(text))
            except Exception as e:
                logging.exception("Whisper failed: %s", e)
                await message.reply("Whisper API でエラーが発生しました。", mention_author=False)
                return

            # 文字起こし結果が空でないかチェック
            if not text or not text.strip():
                await message.reply("文字起こしに失敗したか、音声に内容が含まれていなかったようです。", mention_author=False)
                return

            try:
                summary = await _summarize(text, message.guild.id)
                logging.info("summary done, %d chars", len(summary))
            except Exception as e:
                logging.exception("summarize failed: %s", e)
                await message.reply("要約でエラーが発生しました。", mention_author=False)
                return
        await message.reply(f"🎧 要約はこちら！\n{summary}", mention_author=False)
        pending_urls.pop(message.channel.id, None)
        return
    # -------------------------------------------------------------------------

    # existing /transcribe command
    if content.startswith("!transcribe"):
        await bot.process_commands(message)
        return

    # existing attachment handler
    if message.attachments:
        if not _check_quota(message.guild.id):
            await message.channel.send(_LIMIT_MSG)
            return
        processed = await _process_attachment(message.channel, message.attachments[0], message.author)
        if processed:
            return

    # fallback to default command processing
    await bot.process_commands(message)

@bot.command(name="post")
async def _post(ctx: commands.Context, target: str):
    """ダミー: 今は投稿せず確認用。target=x|note"""
    await ctx.send(f"{target} に投稿（ダミー）: 実装待ち")


@bot.command(name="setprompt")
@commands.has_permissions(administrator=True)
async def _set_prompt(ctx: commands.Context, prompt_type: str = "standfm", *, prompt: str):
    """サーバー専用プロンプトを設定/更新する（管理者専用）
    
    使用方法:
    !setprompt standfm <プロンプト内容>  # スタンドFM URL用プロンプト
    !setprompt file <プロンプト内容>     # ファイルアップロード用プロンプト
    """
    if prompt_type == "standfm":
        _prompt_map[ctx.guild.id] = prompt
        prompt_name = "スタンドFM URL用"
    elif prompt_type == "file":
        _file_prompt_map[ctx.guild.id] = prompt
        prompt_name = "ファイルアップロード用"
    else:
        await ctx.send("プロンプトタイプは 'standfm' または 'file' を指定してください。")
        return
    
    _save_prompts()
    await ctx.send(f"このサーバーの{prompt_name}プロンプトを更新しました。")


@bot.command(name="manual")
async def _manual(ctx: commands.Context):
    """使い方マニュアル（Notion）へのリンクを表示"""
    await ctx.send("使い方マニュアルはこちら:\nhttps://mahogany-people-7f2.notion.site/Bot-217b5414fdf880d6be97ceb8e76c3abd?source=copy_link")


@bot.command(name="prompthelp")
async def _prompt_help(ctx: commands.Context):
    """プロンプト設定コマンドの使い方を表示"""
    help_text = """**プロンプト設定コマンド一覧:**

🔧 **プロンプト設定 (管理者専用)**
`!setprompt standfm <プロンプト内容>` - スタンドFM URL用プロンプトを設定
`!setprompt file <プロンプト内容>` - ファイルアップロード/Discord音声用プロンプトを設定

📖 **プロンプト確認**
`!showprompt standfm` - スタンドFM URL用プロンプトを表示
`!showprompt file` - ファイルアップロード/Discord音声用プロンプトを表示

**使用例:**
```
!setprompt file 以下の音声を要約して、重要なポイントを3つ教えてください。{text}
!showprompt file
```

**対象機能:**
- **スタンドFM**: stand.fmのURL → 「もじ」コマンド
- **ファイル**: m4a/mp3ファイルアップロード、Discord音声メッセージ
"""
    await ctx.send(help_text)


@bot.command(name="showprompt")
async def _show_prompt(ctx: commands.Context, prompt_type: str = "standfm"):
    """現在のサーバープロンプトを表示
    
    使用方法:
    !showprompt standfm  # スタンドFM URL用プロンプト表示
    !showprompt file     # ファイルアップロード用プロンプト表示
    """
    if prompt_type == "standfm":
        prompt = _prompt_map.get(ctx.guild.id, DEFAULT_PROMPT)
        prompt_name = "スタンドFM URL用"
    elif prompt_type == "file":
        prompt = _file_prompt_map.get(ctx.guild.id, DEFAULT_FILE_PROMPT)
        prompt_name = "ファイルアップロード用"
    else:
        await ctx.send("プロンプトタイプは 'standfm' または 'file' を指定してください。")
        return
    
    await ctx.send(f"現在の{prompt_name}プロンプト:\n```{prompt}```")


# ---- Global error logging -------------------------------------------------
@bot.event
async def on_error(event_method: str, *args, **kwargs):
    """Log unhandled exceptions from discord.py events."""
    logging.exception("Unhandled exception in %s", event_method, exc_info=True)


def setup_asyncio_logging():
    """Ensure the default asyncio exception handler logs via logging module."""
    loop = asyncio.get_event_loop()

    def _handler(loop, context):
        exc = context.get("exception")
        if exc:
            logging.exception("Asyncio unhandled exception: %s", exc, exc_info=exc)
        else:
            logging.error("Asyncio error: %s", context.get("message"))

    loop.set_exception_handler(_handler)


setup_asyncio_logging()


if __name__ == "__main__":
    bot.run(TOKEN)
