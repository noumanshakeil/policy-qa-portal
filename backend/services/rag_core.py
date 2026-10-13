"""Lightweight RAG primitives: chunking + lexical ranking + citation packing.

These helpers intentionally avoid a vector DB so the demo runs offline in CI.
Swap `score_chunk` for embedding cosine similarity when you wire pgvector/Qdrant.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_TOKEN = re.compile(r"[a-z0-9]{2,}", re.I)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


def chunk_text(text: str, *, size: int = 420, overlap: int = 60) -> list[str]:
    """Sliding-window chunker with word-ish boundaries."""
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return []
    if len(clean) <= size:
        return [clean]
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        if end < len(clean):
            # Prefer breaking on space.
            space = clean.rfind(" ", start + size // 2, end)
            if space > start:
                end = space
        piece = clean[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def score_chunk(query: str, chunk: str) -> float:
    """Overlap score with light IDF-ish boost for rarer query terms."""
    q = tokenize(query)
    if not q:
        return 0.0
    cset = set(tokenize(chunk))
    if not cset:
        return 0.0
    hits = 0.0
    for term in q:
        if term in cset:
            # Longer tokens get a slight boost (often more specific).
            hits += 1.0 + min(len(term), 12) * 0.02
    return hits / max(len(set(q)), 1)


@dataclass
class Hit:
    chunk_id: str
    document_id: str
    title: str
    text: str
    score: float
    meta: dict


def pack_citations(hits: list[Hit], *, max_chars: int = 1800) -> str:
    """Build a grounded context block for the LLM prompt."""
    parts: list[str] = []
    used = 0
    for i, h in enumerate(hits, start=1):
        block = f"[{i}] ({h.title} / {h.chunk_id}) score={h.score:.2f}\n{h.text}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)
