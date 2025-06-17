from pathlib import Path
from datetime import datetime

import openai

from config import OPENAI_API_KEY
import numpy as np

openai.api_key = OPENAI_API_KEY

def _embed(texts: list[str]):
    """Return numpy array (n, d) embeddings using OpenAI."""
    res = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    # sort to keep original order
    data_sorted = sorted(res.data, key=lambda x: x.index)
    return np.array([d.embedding for d in data_sorted], dtype=np.float32)


def save_and_link(vault_path: Path, title: str, content: str) -> str:
    """Save markdown file and return link text with related notes."""
    vault_path = Path(vault_path)
    vault_path.mkdir(parents=True, exist_ok=True)
    import re
    # sanitize title for filename
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title).replace(" ", "_")[:50]
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_") + f"[{safe_title}].md"
    target = vault_path / filename
    target.write_text(f"# {title}\n\n" + content, encoding="utf-8")

    # find similar docs
    texts = []
    files = list(vault_path.glob("*.md"))
    for f in files:
        if f == target:
            continue
        texts.append(f.read_text(encoding="utf-8"))
    if not texts:
        return filename  # no related
    embeddings = _embed(texts + [content])
    ref = embeddings[-1]
    others = embeddings[:-1]
    sims = (others @ ref) / (np.linalg.norm(others, axis=1) * np.linalg.norm(ref) + 1e-8)
    top_idx = sims.argsort()[-3:][::-1]
    links = [files[i].stem for i in top_idx]

    # append links to file
    with target.open("a", encoding="utf-8") as f:
        f.write("\n\n## 関連メモ\n")
        for l in links:
            f.write(f"- [[{l}]]\n")
    return filename
