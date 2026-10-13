"""News Reader: an LLM reads the article bodies and returns cited claims plus sector direction.

Why this stage exists: headlines and tagged direction alone cannot say WHY a sector is moving or which
funds the news touches. The reader turns ~10 cleaned article bodies into:
  - cited claims (one fact each, tied to an article),
  - an overall tone for the target sector with a one-line reason,
  - the sectors the news helps / hurts (canonical names), used to link news to each fund's holdings.

Every claim is checked against its article (numbers must appear in the source text). If the LLM is
off or fails, a heuristic reader builds claims from the article text so the pipeline still runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.snippet_clean import article_body_for_llm, polish_insight_sentence, sanitize_analyst_bullet
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.query_log import clip_log_text
from news_rag.prompts import build_news_reader_prompt

MAX_ARTICLES = 10
MAX_CLAIMS = 8

READER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tone": {"type": "string"},
        "tone_reason": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "claim": {"type": "string"},
                    "sentiment": {"type": "string"},
                    "article": {"type": "integer"},
                    "mechanism": {"type": "string"},
                    "channel": {"type": "string"},
                    "direction": {"type": "string"},
                    "materiality": {"type": "string"},
                    "confidence": {"type": "string"},
                    "relevance": {"type": "string"},
                },
                "required": ["text", "sentiment", "article"],
            },
        },
        "sectors_positive": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "reason": {"type": "string"}},
            },
        },
        "sectors_negative": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "reason": {"type": "string"}},
            },
        },
        "themes": {"type": "array", "items": {"type": "string"}},
        "net_read": {"type": "string"},
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "dropped_as_noise": {"type": "string"},
    },
    "required": ["tone", "tone_reason", "claims"],
}

READER_SYSTEM = build_news_reader_prompt()


@dataclass
class NewsClaim:
    text: str
    sentiment: str = "neutral"
    article: int = 0  # 1-based index into `NewsRead.articles`
    title: str = ""
    url: str = ""
    source: str = ""
    published: str = ""
    mechanism: str = ""
    channel: str = ""


@dataclass
class SectorCall:
    name: str
    reason: str = ""


@dataclass
class NewsRead:
    tone: str = "unclear"
    tone_reason: str = ""
    claims: list[NewsClaim] = field(default_factory=list)
    sectors_positive: list[SectorCall] = field(default_factory=list)
    sectors_negative: list[SectorCall] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    articles: list[dict[str, Any]] = field(default_factory=list)
    mode: str = "none"  # llm | heuristic | none
    dropped_claims: int = 0

    def positive_names(self) -> list[str]:
        return [s.name for s in self.sectors_positive]

    def negative_names(self) -> list[str]:
        return [s.name for s in self.sectors_negative]

    def direction_for(self, sector_labels: list[str]) -> str:
        """positive / negative / mixed / unknown for any of the given sector labels."""
        labels = [x.lower() for x in sector_labels if x]
        pos = any(_same_sector(p, labels) for p in self.positive_names())
        neg = any(_same_sector(n, labels) for n in self.negative_names())
        if pos and neg:
            return "mixed"
        if pos:
            return "positive"
        if neg:
            return "negative"
        return "unknown"

    def reason_for(self, sector_labels: list[str]) -> str:
        labels = [x.lower() for x in sector_labels if x]
        for s in self.sectors_positive + self.sectors_negative:
            if _same_sector(s.name, labels) and s.reason:
                return s.reason
        return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "tone": self.tone,
            "tone_reason": self.tone_reason,
            "themes": self.themes,
            "claims": [
                {"text": c.text, "sentiment": c.sentiment, "article": c.article, "title": c.title, "url": c.url}
                for c in self.claims
            ],
            "sectors_positive": [{"name": s.name, "reason": s.reason} for s in self.sectors_positive],
            "sectors_negative": [{"name": s.name, "reason": s.reason} for s in self.sectors_negative],
            "articles_read": len(self.articles),
            "dropped_claims": self.dropped_claims,
        }


def _same_sector(name: str, labels: list[str]) -> bool:
    n = (name or "").strip().lower()
    if not n:
        return False
    for lab in labels:
        if n == lab or n in lab or lab in n:
            return True
    return False


# ---------------------------------------------------------------------------
# Article preparation
# ---------------------------------------------------------------------------


def _impact(a: dict[str, Any]) -> float:
    try:
        return float(a.get("max_impact") or a.get("impact") or 0)
    except (TypeError, ValueError):
        return 0.0


def select_articles(articles: list[dict[str, Any]], limit: int = MAX_ARTICLES) -> list[dict[str, Any]]:
    """Highest impact first, one article per title, newest breaks ties."""
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for a in articles:
        if not isinstance(a, dict):
            continue
        key = re.sub(r"\W+", " ", str(a.get("title") or "")).strip().lower()[:90] or str(a.get("url") or "")
        if not key or key in seen:
            continue
        body = _body(a)
        title = str(a.get("title") or "")
        from news_rag.snippet_clean import article_text_usable, starts_mid_sentence

        if body and not article_text_usable(body) and (starts_mid_sentence(title) or not article_text_usable(title)):
            continue
        seen.add(key)
        uniq.append(a)
    attr = [a for a in uniq if a.get("_attr_sector")]
    rest = [a for a in uniq if not a.get("_attr_sector")]
    ordered = attr + rest
    ordered.sort(key=lambda a: (_impact(a) + (2 if a.get("_attr_sector") else 0), str(a.get("published_at") or "")), reverse=True)
    return ordered[:limit]


def _article_char_limit() -> int:
    settings = get_settings()
    cap = int(getattr(settings, "insight_llm_article_chars", 0) or 0)
    return max(cap, int(settings.snippet_chars))


def _body(a: dict[str, Any], chars: int | None = None) -> str:
    limit = int(chars) if chars is not None else _article_char_limit()
    text = article_body_for_llm(a, limit=limit)
    title = str(a.get("title") or "").strip()
    if title and text.lower().startswith(title.lower()[: min(50, len(title))]):
        text = text[len(title) :].lstrip(" :-—")
    return text.strip()


def _date(a: dict[str, Any]) -> str:
    return str(a.get("published_at") or a.get("date") or "")[:10]


def _numbers(text: str) -> set[str]:
    return {m.replace(",", "") for m in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text or "")}


def _allowed_sector_names() -> list[str]:
    try:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

        return list(get_sector_fund_ranking_index().sector_names)
    except Exception:
        return []


def _canonical_sector(name: str, allowed: list[str]) -> str:
    n = (name or "").strip().lower()
    if not n:
        return ""
    for a in allowed:
        if a.lower() == n:
            return a
    for a in allowed:
        if n in a.lower() or a.lower() in n:
            return a
    return ""


def _target_label(brief: QuestionBrief) -> str:
    sector = brief.primary_sector()
    if sector:
        return f"sector: {sector}"
    if brief.drivers:
        return "driver: " + ", ".join(d.replace("_", " ") for d in brief.drivers)
    if brief.raw.get("attribution_target"):
        return "sectors inside the fund: " + str(brief.raw["attribution_target"])
    if brief.funds:
        return "fund: " + ", ".join(brief.funds[:2])
    return "market overview"


# ---------------------------------------------------------------------------
# LLM reader
# ---------------------------------------------------------------------------


def _build_user_prompt(question: str, brief: QuestionBrief, arts: list[dict[str, Any]], allowed: list[str]) -> str:
    lines = [
        f"QUESTION: {question}",
        f"TARGET: {_target_label(brief)}",
        f"ALLOWED_SECTORS: {', '.join(allowed) if allowed else '(none)'}",
        "",
        "ARTICLES:",
    ]
    for i, a in enumerate(arts, 1):
        tag = f"{_date(a)} | tagged {a.get('direction') or 'n/a'} impact {a.get('max_impact') or 'n/a'}"
        lines.append(f"[{i}] ({tag}) {str(a.get('title') or '').strip()}")
        lines.append(_body(a))
        lines.append("")
    return "\n".join(lines)


def _direction_to_sentiment(direction: str) -> str:
    d = (direction or "").strip().lower()
    if d in ("positive", "negative", "neutral"):
        return d
    if d == "mixed":
        return "neutral"
    return "neutral"


def _normalize_claim_dict(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    text = str(out.get("text") or out.get("claim") or "").strip()
    out["text"] = text
    if not out.get("sentiment"):
        out["sentiment"] = _direction_to_sentiment(str(out.get("direction") or ""))
    mech = str(out.get("mechanism") or "").strip()
    if mech and mech not in text:
        out["text"] = f"{text} ({mech})" if text else mech
    return out


def _clean_claims(
    raw_claims: list[Any], arts: list[dict[str, Any]]
) -> tuple[list[NewsClaim], int]:
    out: list[NewsClaim] = []
    dropped = 0
    seen: set[str] = set()
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        item = _normalize_claim_dict(item)
        text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        try:
            idx = int(item.get("article") or 0)
        except (TypeError, ValueError):
            idx = 0
        if not text or not (1 <= idx <= len(arts)):
            dropped += 1
            continue
        art = arts[idx - 1]
        source_text = f"{art.get('title') or ''} {_body(art)}"
        if not _numbers(text) <= _numbers(source_text):
            dropped += 1  # a number the article never printed
            continue
        key = text.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        sent = str(item.get("sentiment") or "neutral").lower()
        if sent not in ("positive", "negative", "neutral"):
            sent = "neutral"
        claim_text = polish_insight_sentence(text, max_chars=220) or text
        out.append(
            NewsClaim(
                text=claim_text,
                sentiment=sent,
                article=idx,
                title=str(art.get("title") or "").strip(),
                url=str(art.get("url") or ""),
                source=str(art.get("source") or ""),
                published=_date(art),
                mechanism=str(item.get("mechanism") or "").strip(),
                channel=str(item.get("channel") or "").strip(),
            )
        )
        if len(out) >= MAX_CLAIMS:
            break
    return out, dropped


def _clean_sector_calls(raw: Any, allowed: list[str]) -> list[SectorCall]:
    out: list[SectorCall] = []
    seen: set[str] = set()
    for item in raw or []:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        name = _canonical_sector(str(item.get("name") or ""), allowed) if allowed else str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        reason = polish_insight_sentence(str(item.get("reason") or ""), max_chars=180)
        out.append(SectorCall(name=name, reason=reason))
    return out


def _llm_read(
    question: str, brief: QuestionBrief, arts: list[dict[str, Any]], query_log: Any
) -> NewsRead | None:
    settings = get_settings()
    allowed = _allowed_sector_names()
    user = _build_user_prompt(question, brief, arts, allowed)
    try:
        res = call_json_llm(
            system_prompt=READER_SYSTEM,
            user_content=user,
            context_blocks=[],
            model_override=router_model(settings),
            max_tokens=4000,
            temperature=0.0,
            query_log=query_log,
            response_schema=READER_SCHEMA,
            stage="news_reader",
        )
    except Exception as exc:  # noqa: BLE001
        if query_log is not None:
            query_log.write(f"NEWS_READER llm_failed error={clip_log_text(str(exc), 200)}")
        return None
    parsed = res.parsed if isinstance(res.parsed, dict) else {}
    if not parsed.get("claims"):
        return None
    claims, dropped = _clean_claims(parsed.get("claims") or [], arts)
    if not claims:
        return None
    tone = str(parsed.get("tone") or "unclear").lower()
    if tone not in ("positive", "negative", "mixed", "unclear"):
        tone = "unclear"
    themes = [str(t).strip() for t in (parsed.get("themes") or []) if str(t).strip()][:4]
    tone_reason = sanitize_analyst_bullet(str(parsed.get("tone_reason") or "")) or re.sub(
        r"\s+", " ", str(parsed.get("tone_reason") or "")
    ).strip()
    if not tone_reason:
        tone_reason = sanitize_analyst_bullet(str(parsed.get("net_read") or "")) or str(
            parsed.get("net_read") or ""
        ).strip()
    return NewsRead(
        tone=tone,
        tone_reason=tone_reason,
        claims=claims,
        sectors_positive=_clean_sector_calls(parsed.get("sectors_positive"), allowed),
        sectors_negative=_clean_sector_calls(parsed.get("sectors_negative"), allowed),
        themes=themes,
        articles=arts,
        mode="llm",
        dropped_claims=dropped,
    )


# ---------------------------------------------------------------------------
# Heuristic reader (no LLM)
# ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _first_fact(a: dict[str, Any]) -> str:
    from news_rag.snippet_clean import article_text_usable, starts_mid_sentence

    body = _body(a)
    for sent in _SENT_SPLIT.split(body):
        s = sent.strip()
        if not (40 <= len(s) <= 220):
            continue
        if starts_mid_sentence(s) or not article_text_usable(s):
            continue
        if re.search(r"\d|%|rise|fall|grow|decline|demand|sales|cost|price", s, re.I):
            return s
    title = str(a.get("title") or "").strip()
    return title[:200]


def _heuristic_read(brief: QuestionBrief, arts: list[dict[str, Any]]) -> NewsRead:
    claims: list[NewsClaim] = []
    pos = neg = 0
    for i, a in enumerate(arts, 1):
        d = str(a.get("direction") or "neutral").lower()
        if d == "positive":
            pos += 1
        elif d == "negative":
            neg += 1
        text = _first_fact(a)
        if not text:
            continue
        claims.append(
            NewsClaim(
                text=text,
                sentiment=d if d in ("positive", "negative") else "neutral",
                article=i,
                title=str(a.get("title") or "").strip(),
                url=str(a.get("url") or ""),
                source=str(a.get("source") or ""),
                published=_date(a),
            )
        )
        if len(claims) >= 5:
            break
    tone = "unclear"
    if pos > neg * 1.25 and pos:
        tone = "positive"
    elif neg > pos * 1.25 and neg:
        tone = "negative"
    elif pos or neg:
        tone = "mixed"
    sector = brief.primary_sector()
    sp = [SectorCall(sector)] if sector and tone in ("positive", "mixed") else []
    sn = [SectorCall(sector)] if sector and tone in ("negative", "mixed") else []
    return NewsRead(
        tone=tone,
        tone_reason="",
        claims=claims,
        sectors_positive=sp,
        sectors_negative=sn,
        articles=arts,
        mode="heuristic",
    )


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def read_news(
    question: str,
    brief: QuestionBrief,
    articles: list[dict[str, Any]],
    *,
    query_log: Any = None,
) -> NewsRead:
    arts = select_articles(articles)
    if not arts:
        return NewsRead(mode="none")
    settings = get_settings()
    use_llm = bool(getattr(settings, "insight_use_llm_news_reader", True)) and llm_api_key_configured(settings)
    result: NewsRead | None = None
    if use_llm:
        result = _llm_read(question, brief, arts, query_log)
    if result is None:
        result = _heuristic_read(brief, arts)
    if query_log is not None:
        query_log.log_news_read(result.to_dict())
    return result
