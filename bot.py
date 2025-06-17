import logging
from pathlib import Path

from config import DISCORD_BOT_TOKEN, VAULT_PATH

import discord
from discord import File, Interaction
from discord.ext import commands

from utils.speech import transcribe
from utils.summarize import summarize


import re, asyncio, os, tempfile, subprocess, httpx
from pydub import AudioSegment
from openai import OpenAI
from datetime import date

STANDFM_RE = re.compile(r'https?://stand\.fm/episodes/[0-9a-f]+')
# no keyword triggers, use two-step flow
pending_urls: dict[int, str] = {}  # channel_id -> url
MAX_SECONDS = 20 * 60  # 20 minutes
openai_client = OpenAI()

# --- Daily quota control ----------------------------------------------------
_DAILY_LIMIT = 5
_usage_count = 0
_usage_date = date.today()
_LIMIT_MSG = (
    "残念！スタンダードプランでは1日5回までです。"
    "6回以上使いたい場合は月5$のプレミアムプランに入っていいかオーナーさんにおねだりしてみてね！"
)

def _check_quota() -> bool:
    """Return True if processing is allowed, otherwise False and sends limit msg."""
    global _usage_count, _usage_date
    today = date.today()
    if today != _usage_date:
        _usage_date = today
        _usage_count = 0
    if _usage_count >= _DAILY_LIMIT:
        return False
    _usage_count += 1
    return True

async def _yt_download(url: str, dst: str):
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "-f", "bestaudio", "-o", dst, url
    )
    await proc.communicate()


def _trim(src: str, dst: str):
    audio = AudioSegment.from_file(src)
    audio[: MAX_SECONDS * 1000].export(dst, format="mp3")


async def _whisper(path: str) -> str:
    with open(path, "rb") as f:
        res = openai_client.audio.transcriptions.create(
            file=f, model="whisper-1", language="ja"
        )
    return res.text


async def _summarize(text: str) -> str:
    prompt = (
        "あなたは気さくなラジオ編集者です。\n"
        "以下を 3 行でざっくり要約し、最後に作者が最も伝えたいであろうメッセージを 1 行で書いてください。\n\n"
        f"{text}"
    )
    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content.strip()

logging.basicConfig(level=logging.INFO)

# Load credentials from .env (handled by python-dotenv in config.py)
TOKEN = DISCORD_BOT_TOKEN
if TOKEN is None:
    raise RuntimeError("DISCORD_BOT_TOKEN must be set in .env")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


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
    # Ignore own bot messages
    if message.author.bot:
        return

    content = message.content

        # --- stand.fm URL storage -------------------------------------------------
    m = STANDFM_RE.search(content)
    if m:
        pending_urls[message.channel.id] = m.group(0)
        await message.add_reaction("👍")
        return

    # --- Trigger by exact 'もじ' ---------------------------------------------
    if content.strip() == "もじ":
        url = pending_urls.get(message.channel.id)
        if not url:
            await message.reply("先に stand.fm のエピソード URL を送ってください。", mention_author=False)
            return
        if not _check_quota():
            await message.reply(_LIMIT_MSG, mention_author=False)
            return
        await message.channel.typing()
        with tempfile.TemporaryDirectory() as td:
            raw = os.path.join(td, "raw.m4a")
            await _yt_download(url, raw)

            work = raw
            try:
                dur = AudioSegment.from_file(raw).duration_seconds
            except Exception:
                dur = 0
            if dur > MAX_SECONDS:
                work = os.path.join(td, "trim.mp3")
                _trim(raw, work)

            text = await _whisper(work)
            summary = await _summarize(text)
        await message.reply(f"🎧 要約はこちら！\n{summary}", mention_author=False)
        pending_urls.pop(message.channel.id, None)
        return
    # -------------------------------------------------------------------------

    # existing /transcribe command
    if content.startswith("/transcribe"):
        await bot.process_commands(message)
        return

    # existing attachment handler
    if message.attachments:
        if not _check_quota():
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


if __name__ == "__main__":
    bot.run(TOKEN)
