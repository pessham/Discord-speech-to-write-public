import os

from config import OPENAI_API_KEY
from pathlib import Path
import subprocess, tempfile

import openai

# --- API KEY SETUP ---------------------------------------------------------
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY must be set in .env")

# ---------------------------------------------------------------------------

# supported container/codec combos openai reliably accepts
SUPPORTED_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}

def _convert_to_mp3(src: Path) -> Path:
    """Convert audio to mp3 16kHz mono using ffmpeg and return new Path."""
    dst = Path(tempfile.gettempdir()) / (src.stem + "_conv.mp3")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "24k",
        str(dst),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 変換に失敗しました。ffmpeg がインストールされているか確認してください。\n" + result.stderr.decode(errors="ignore"))
    return dst

def _convert_to_wav(src: Path) -> Path:
    """Convert audio to wav 16kHz mono using ffmpeg and return new Path."""
    dst = Path(tempfile.gettempdir()) / (src.stem + "_conv.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(dst),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 変換に失敗しました。ffmpeg がインストールされているか確認してください。\n" + result.stderr.decode(errors="ignore"))
    return dst

def _ensure_supported(path: Path) -> Path:
    if path.suffix.lower() in SUPPORTED_EXT:
        return path
    # fallback convert
    return _convert_to_mp3(path)

audio_model = "whisper-1"

def _transcribe_once(path: Path):
    with open(path, "rb") as f:
        return openai.audio.transcriptions.create(model=audio_model, file=f).text.strip()

def transcribe(file_path: Path) -> str:
     """Robust transcription helper.
 
     1. まず 24kbps の MP3 (16 kHz mono) に変換して Whisper に送る。
     2. もし MP3 が拒否された場合のみ WAV へフォールバック。
     この順序により 60 分音声でも 25 MB 未満に収まり、長尺でも安定して文字起こしが可能。
     """
     try:
         mp3 = _convert_to_mp3(file_path)
         return _transcribe_once(mp3)
     except Exception:
         # Fallback to WAV if MP3 fails for何らかの理由 (稀)
         wav = _convert_to_wav(file_path)
         return _transcribe_once(wav)
