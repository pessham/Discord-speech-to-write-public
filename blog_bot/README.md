# blog_bot

Generate Japanese blog articles in Markdown using Anthropic Claude.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-...
```

## Usage
```bash
python main.py "副業 ブログ 稼ぎ方" "AI 文章術"
```

Markdown files are saved under `output/`.
