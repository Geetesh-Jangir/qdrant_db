"""FastAPI app: ask questions against Qdrant Cloud news corpus."""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from news_rag.answer import empty_answer, generate_answer
from news_rag.config import get_settings
from news_rag.query_log import new_query_logger
from news_rag.retrieve import retrieve_for_question

_STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="News RAG", version="1.0.0")
if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    stock: str | None = Field(default=None, max_length=200)
    date_from: str | None = Field(default=None, max_length=32)
    date_to: str | None = Field(default=None, max_length=32)
    min_impact: int | None = Field(default=None, ge=0, le=3)
    source: str | None = Field(default=None, max_length=120)
    direction: str | None = Field(default=None, max_length=20)


def _check_token(authorization: str | None, x_app_token: str | None) -> None:
    settings = get_settings()
    token = (settings.app_token or "").strip()
    if not token:
        return
    supplied = (x_app_token or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization.split(" ", 1)[1].strip()
    if supplied != token:
        raise HTTPException(status_code=401, detail="Invalid or missing app token")


@app.get("/")
def index() -> FileResponse:
    page = _STATIC / "index.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="index.html missing")
    return FileResponse(page)


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "ok": True,
        "collection": settings.qdrant_collection,
        "deepseek_model": settings.deepseek_model,
    }


@app.post("/api/ask")
def ask(
    body: AskRequest,
    authorization: str | None = Header(default=None),
    x_app_token: str | None = Header(default=None),
) -> dict:
    _check_token(authorization, x_app_token)
    settings = get_settings()
    if not settings.qdrant_url:
        raise HTTPException(status_code=500, detail="QDRANT_URL not configured")
    if not settings.qdrant_api_key and "cloud.qdrant.io" in settings.qdrant_url:
        raise HTTPException(status_code=500, detail="QDRANT_API_KEY required for Cloud")

    query_log = new_query_logger()
    query_log.log_request(
        {
            "question": body.question,
            "stock": body.stock,
            "date_from": body.date_from,
            "date_to": body.date_to,
            "min_impact": body.min_impact,
            "source": body.source,
            "direction": body.direction,
        }
    )

    article_count = 0
    try:
        parsed, articles = retrieve_for_question(
            body.question,
            stock=body.stock,
            date_from=body.date_from,
            date_to=body.date_to,
            min_impact=body.min_impact,
            source=body.source,
            direction=body.direction,
            query_log=query_log,
        )
        article_count = len(articles)

        if not articles:
            result = empty_answer(parsed)
            result["insight_source"] = "no_articles"
            query_log.log_insight_output(
                insight_source="no_articles",
                char_count=len(result.get("insight") or ""),
                preview=str(result.get("insight") or ""),
            )
            meta = query_log.finish(
                outcome="no_articles",
                article_count=0,
                insight_source="no_articles",
            )
            result["query_log_id"] = meta["query_id"]
            result["query_log_file"] = meta["log_file"]
            result["deepseek_calls"] = meta["deepseek_calls"]
            result["deepseek_input_tokens"] = meta["deepseek_input_tokens"]
            result["deepseek_output_tokens"] = meta["deepseek_output_tokens"]
            return result

        if not settings.deepseek_api_key:
            query_log.log_error("config", "DEEPSEEK_API_KEY not configured")
            query_log.finish(outcome="error", article_count=len(articles))
            raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY not configured")

        result = generate_answer(parsed, articles, query_log=query_log)
        meta = query_log.finish(
            outcome="ok",
            article_count=len(articles),
            insight_source=str(result.get("insight_source") or ""),
        )
        result["query_log_id"] = meta["query_id"]
        result["query_log_file"] = meta["log_file"]
        result["deepseek_calls"] = meta["deepseek_calls"]
        result["deepseek_input_tokens"] = meta["deepseek_input_tokens"]
        result["deepseek_output_tokens"] = meta["deepseek_output_tokens"]
        return result
    except httpx.HTTPError as exc:
        query_log.log_error("deepseek", str(exc))
        query_log.finish(outcome="deepseek_error", article_count=article_count)
        raise HTTPException(status_code=502, detail=f"DeepSeek request failed: {exc}") from exc
    except Exception as exc:
        query_log.log_error("unhandled", str(exc))
        query_log.finish(outcome="error", article_count=article_count)
        raise
