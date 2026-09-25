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
from news_rag.llm_client import llm_api_key_configured, llm_model, llm_provider, missing_llm_key_message
from news_rag.query_log import new_query_logger
from news_rag.fund_brief import generate_fund_brief, list_portfolio_funds
from news_rag.retrieve import retrieve_for_question

_STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="News RAG", version="1.0.0")
if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


class FundBriefRequest(BaseModel):
    isin: str = Field(min_length=10, max_length=20)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    stock: str | None = Field(default=None, max_length=200)
    date_from: str | None = Field(default=None, max_length=32)
    date_to: str | None = Field(default=None, max_length=32)
    min_impact: int | None = Field(default=None, ge=0, le=3)
    source: str | None = Field(default=None, max_length=120)
    direction: str | None = Field(default=None, max_length=20)


def _attach_llm_meta(result: dict, meta: dict) -> None:
    result["query_log_id"] = meta["query_id"]
    result["query_log_file"] = meta["log_file"]
    result["llm_provider"] = meta.get("llm_provider") or ""
    result["llm_calls"] = meta["llm_calls"]
    result["llm_input_tokens"] = meta["llm_input_tokens"]
    result["llm_output_tokens"] = meta["llm_output_tokens"]
    result["deepseek_calls"] = meta["deepseek_calls"]
    result["deepseek_input_tokens"] = meta["deepseek_input_tokens"]
    result["deepseek_output_tokens"] = meta["deepseek_output_tokens"]


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


@app.get("/fund")
def fund_page() -> FileResponse:
    page = _STATIC / "fund.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="fund.html missing")
    return FileResponse(page)


@app.get("/api/portfolio-funds")
def portfolio_funds(
    authorization: str | None = Header(default=None),
    x_app_token: str | None = Header(default=None),
) -> dict:
    _check_token(authorization, x_app_token)
    settings = get_settings()
    if not (settings.portfolio_json or "").strip():
        raise HTTPException(status_code=400, detail="PORTFOLIO_JSON not configured")
    try:
        funds = list_portfolio_funds(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"funds": funds}


@app.post("/api/fund-brief")
def fund_brief(
    body: FundBriefRequest,
    authorization: str | None = Header(default=None),
    x_app_token: str | None = Header(default=None),
) -> dict:
    _check_token(authorization, x_app_token)
    settings = get_settings()
    if not settings.qdrant_url:
        raise HTTPException(status_code=500, detail="QDRANT_URL not configured")
    if not (settings.portfolio_json or "").strip():
        raise HTTPException(status_code=400, detail="PORTFOLIO_JSON not configured")
    if not llm_api_key_configured(settings):
        raise HTTPException(status_code=500, detail=missing_llm_key_message())
    try:
        return generate_fund_brief(body.isin.strip(), settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "ok": True,
        "collection": settings.qdrant_collection,
        "llm_provider": llm_provider(settings),
        "llm_model": llm_model(settings),
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
            _attach_llm_meta(result, meta)
            return result

        if not llm_api_key_configured(settings):
            message = missing_llm_key_message(settings)
            query_log.log_error("config", message)
            query_log.finish(outcome="error", article_count=len(articles))
            raise HTTPException(status_code=500, detail=message)

        result = generate_answer(parsed, articles, query_log=query_log)
        meta = query_log.finish(
            outcome="ok",
            article_count=len(articles),
            insight_source=str(result.get("insight_source") or ""),
        )
        _attach_llm_meta(result, meta)
        return result
    except httpx.HTTPError as exc:
        provider = llm_provider(get_settings())
        query_log.log_error("llm", str(exc))
        query_log.finish(outcome="llm_error", article_count=article_count)
        raise HTTPException(status_code=502, detail=f"{provider} request failed: {exc}") from exc
    except Exception as exc:
        query_log.log_error("unhandled", str(exc))
        query_log.finish(outcome="error", article_count=article_count)
        raise
