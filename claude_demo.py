"""Simple demo script that sends a greeting to Claude via the Anthropic API and prints the response.

Prerequisites:
1. `pip install -r requirements.txt` (anthropic package is required)
2. Set an environment variable `ANTHROPIC_API_KEY` with your Claude API key.
   On Windows PowerShell:
       $Env:ANTHROPIC_API_KEY = "sk-..."

Run the script:
    python claude_demo.py
"""

import os
from dotenv import load_dotenv
import anthropic

# Load environment variables from a local .env file if present.
load_dotenv()


def main() -> None:
    # Ensure the API key is available.
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Environment variable ANTHROPIC_API_KEY is not set. Please export your API key and try again."
        )

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=64,
        messages=[{"role": "user", "content": "Hello Claude!"}],
    )

    # The SDK returns content as a list of blocks; take the first block's text.
    text = response.content[0].text if response.content else "<no content>"
    print("Claude:", text)


if __name__ == "__main__":
    main()
