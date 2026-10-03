"""Map fund holding labels to Qdrant entity_names (Ltd. vs Limited, etc.)."""

from __future__ import annotations

import re

from news_rag.entity_index import corpus_entity_names

_SUFFIX_VARIANTS = (
    (re.compile(r"\bLtd\.?\s*$", re.I), "Limited"),
    (re.compile(r"\bLimited\s*$", re.I), "Ltd."),
)


def _normalize_key(name: str) -> str:
    s = re.sub(r"[^\w\s]", " ", (name or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def resolve_corpus_entity(holding_name: str, corpus: set[str] | None = None) -> str:
    """Best corpus entity label for a fund holding name."""
    raw = (holding_name or "").strip()
    if not raw:
        return raw
    names = corpus if corpus is not None else corpus_entity_names()
    if raw in names:
        return raw
    candidates = [
        raw,
        raw.replace(" Ltd.", " Limited").replace(" Ltd", " Limited"),
        raw.replace(" Limited", " Ltd.").replace(" Limited", " Ltd"),
        re.sub(r"\bLtd\.?\b", "Limited", raw, flags=re.I),
    ]
    for c in candidates:
        if c in names:
            return c
    key = _normalize_key(raw)
    for label in names:
        if _normalize_key(label) == key:
            return label
    # Prefix match on first two tokens (e.g. "ICICI Bank")
    parts = [p for p in re.findall(r"[A-Za-z&]+", raw) if len(p) > 1]
    if len(parts) >= 2:
        prefix = f"{parts[0]} {parts[1]}".lower()
        best: tuple[int, str] | None = None
        for label in names:
            if prefix in _normalize_key(label):
                score = len(label)
                if best is None or score < best[0]:
                    best = (score, label)
        if best:
            return best[1]
    return raw


def resolve_corpus_entities(holding_names: list[str]) -> list[str]:
    corpus = corpus_entity_names()
    seen: set[str] = set()
    out: list[str] = []
    for name in holding_names:
        resolved = resolve_corpus_entity(name, corpus)
        if resolved and resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out
