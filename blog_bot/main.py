"""Blog article generator using Anthropic Claude.
Usage:
    python main.py "keyword one" "keyword two" ...

Creates markdown files under ./output.
"""
from __future__ import annotations
import os, sys, json, textwrap
from pathlib import Path
import click
from dotenv import load_dotenv
import anthropic

load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("ANTHROPIC_API_KEY not set, copy .env.example to .env and fill it.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

PROMPT_TMPL = (
    "You are a professional blog writer. Write a Japanese blog post of about 1200 characters "
    "optimized for SEO on the topic: '{keyword}'. Use Markdown headings and include an introduction, "
    "three key sections, and a conclusion. Title should be an H1 at the top."
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_article(keyword: str) -> str:
    prompt = PROMPT_TMPL.format(keyword=keyword)
    msg = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


@click.command()
@click.argument("keywords", nargs=-1, required=True)
def main(keywords: tuple[str]):
    """Generate articles for provided KEYWORDS."""
    for kw in keywords:
        md = generate_article(kw)
        fname = OUTPUT_DIR / f"{kw.replace(' ', '_')}.md"
        fname.write_text(md, encoding="utf-8")
        click.echo(f"Generated {fname}")


if __name__ == "__main__":
    main()
