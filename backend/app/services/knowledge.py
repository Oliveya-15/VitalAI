"""RAG-lite: TF-IDF retrieval over a curated health knowledge base (NLP, no external API)."""
from __future__ import annotations

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "health_kb.json"
_docs: list[dict] = []
_vec: TfidfVectorizer | None = None
_matrix = None


def _init() -> None:
    global _docs, _vec, _matrix
    if _vec is not None:
        return
    _docs = json.loads(_KB_PATH.read_text(encoding="utf-8"))
    corpus = [f"{d['title']}. {d['title']}. {d['text']}" for d in _docs]
    _vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    _matrix = _vec.fit_transform(corpus)


def search(query: str, k: int = 3, min_score: float = 0.08) -> list[dict]:
    _init()
    sims = cosine_similarity(_vec.transform([query]), _matrix)[0]
    ranked = sorted(range(len(_docs)), key=lambda i: sims[i], reverse=True)[:k]
    return [
        {"id": _docs[i]["id"], "title": _docs[i]["title"], "text": _docs[i]["text"], "score": round(float(sims[i]), 3)}
        for i in ranked
        if sims[i] >= min_score
    ]
