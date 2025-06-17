import os

from config import OPENAI_API_KEY
import openai

# APIキー設定
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY must be set in .env")


def summarize(text: str) -> dict:
    """Return dict with summary(<=100chars) and x_tweet."""
    prompt = (
        "次の日本語テキストを読み、100文字程度で内容要約を1つ作成してください。その後、以下のSNS投稿テンプレートに従ってX(Twitter)用投稿文を作成してください。note用出力は不要です。\n"
        "\n【テンプレート】\n"
        "1. 読者への問い掛けや断定\n"
        "2. 重要ポイント箇条書き(2~3行)\n"
        "3. 筆者の体験談1行\n"
        "4. 主張を強める or エモい一言\n"
        "5. 行動を促す呼び掛け\n"
        "\n制約:\n- フレンドリーで信頼感のある語り口\n- 行動を促す言葉を含める\n- 体験談でリアルさを出す\n- テンポよく140字以内\n"
        "\n--- 入力テキスト ---\n" + text + "\n--------------------"
    )
    response = openai.chat.completions.create(
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
