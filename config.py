"""Centralized configuration using environment variables.
Requires a `.env` file in project root. See `.env.example`."""

from pathlib import Path
from dotenv import load_dotenv
import os

# load .env once at import
load_dotenv()

# Discord
DISCORD_BOT_TOKEN: str | None = os.getenv("DISCORD_BOT_TOKEN")

# Vault path for Obsidian markdown storage
VAULT_PATH_STR: str | None = os.getenv("VAULT_PATH")
VAULT_PATH: Path | None = Path(VAULT_PATH_STR) if VAULT_PATH_STR else None

# OpenAI credentials
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# Twitter / X API (optional)
X_CONSUMER_KEY: str | None = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET: str | None = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN: str | None = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET: str | None = os.getenv("X_ACCESS_SECRET")
