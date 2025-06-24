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
_prompt_map: dict[int, str] = {}
if _PROMPT_FILE.exists():
    try:
        _prompt_map.update(json.loads(_PROMPT_FILE.read_text(encoding="utf-8")))
    except Exception as e:
        logging.warning("Failed to load prompts.json: %s", e)

def _save_prompts():
    try:
        _PROMPT_FILE.write_text(json.dumps(_prompt_map, ensure_ascii=False, indent=2), encoding="utf-8")
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

async def _yt_download(url: str, dst: str) -> bool:
    """Download audio. Return True on success, False otherwise (e.g. private)."""
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "-f", "bestaudio", "-o", dst, url,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    return proc.returncode == 0


def _trim(src: str, dst: str):
    audio = AudioSegment.from_file(src)
    audio[: MAX_SECONDS * 1000].export(dst, format="mp3")


async def _whisper(path: str) -> str:
    """Transcribe audio using utils.speech which converts to 24kbps MP3 before upload."""
    return await asyncio.to_thread(whisper_transcribe, Path(path))


async def _summarize(text: str, guild_id: int) -> str:
    tmpl = _prompt_map.get(guild_id, DEFAULT_PROMPT)
    prompt = tmpl.format(text=text)
    def _do() -> str:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
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
    await channel.send("文字起こし中…")
    transcript = transcribe(file_path)
    await channel.send("要約中…")
    parts = summarize(transcript)
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
            success = await _yt_download(url, raw)
            if not success:
                await message.reply("僕はメンバーシップなど公開されていない放送の文字おこしは出来ないよ！誰でも聴くことが出来る放送をアップしてね！", mention_author=False)
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
async def _set_prompt(ctx: commands.Context, *, prompt: str):
    """サーバー専用プロンプトを設定/更新する（管理者専用）"""
    _prompt_map[ctx.guild.id] = prompt
    _save_prompts()
    await ctx.send("このサーバーのプロンプトを更新しました。")


@bot.command(name="manual")
async def _manual(ctx: commands.Context):
    """使い方マニュアル（Notion）へのリンクを表示"""
    await ctx.send("使い方マニュアルはこちら:\nhttps://mahogany-people-7f2.notion.site/Bot-217b5414fdf880d6be97ceb8e76c3abd?source=copy_link")


@bot.command(name="showprompt")
async def _show_prompt(ctx: commands.Context):
    """現在のサーバープロンプトを表示"""
    prompt = _prompt_map.get(ctx.guild.id, DEFAULT_PROMPT)
    await ctx.send(f"現在のプロンプト:\n```{prompt}```")


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
