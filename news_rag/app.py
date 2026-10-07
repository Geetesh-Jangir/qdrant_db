"""FastAPI app: ask questions against Qdrant Cloud news corpus."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from historical_data.nav_service import get_fund_nav_history
from news_rag.config import get_settings
from news_rag.fund_search import get_fund_index
from news_rag.llm_client import (
    llm_api_key_configured,
    llm_model,
    llm_provider,
    missing_llm_key_message,
    reset_llm_request_state,
)
from news_rag.query_log import new_fund_brief_logger, new_query_logger
from news_rag.fund_brief import generate_fund_brief
from news_rag.ask_engine import run_ask_engine
from news_rag.embed import embeddings_ready
from news_rag.sector_fund_ranking import sector_ranking_data_available
from news_rag.stock_fund_ranking import holdings_archive_available

_STATIC = Path(__file__).resolve().parent / "static"

logger = logging.getLogger(__name__)


def _warmup_embeddings_background() -> None:
    settings = get_settings()
    if not settings.rag_warmup_embeddings:
        return

    def _run() -> None:
        try:
            from news_rag.embed import embed_query

            embed_query("warmup")
            logger.info("embedding warmup finished")
        except Exception as exc:
            logger.warning("embedding warmup failed: %s", exc)

    threading.Thread(target=_run, name="embedding-warmup", daemon=True).start()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _warmup_embeddings_background()
    yield


app = FastAPI(title="News RAG", version="1.0.0", lifespan=_lifespan)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if not isinstance(detail, (str, dict, list)):
            detail = str(detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
    logger.exception("unhandled_request_error")
    return JSONResponse(status_code=500, content={"detail": str(exc)[:800]})


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
    result["query_summary_json"] = meta.get("summary_json") or ""
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


_HTML_NO_CACHE = {"Cache-Control": "no-cache"}


def _html_page(filename: str) -> FileResponse:
    page = _STATIC / filename
    if not page.is_file():
        raise HTTPException(status_code=404, detail=f"{filename} missing")
    return FileResponse(page, headers=_HTML_NO_CACHE)


@app.get("/")
def index() -> FileResponse:
    return _html_page("index.html")


@app.get("/fund")
def fund_page() -> FileResponse:
    return _html_page("fund.html")


@app.get("/fund-search")
def fund_search_page() -> FileResponse:
    return _html_page("fund_search.html")


@app.get("/api/funds/search")
def search_funds(
    q: str = "",
    limit: int = 15,
    authorization: str | None = Header(default=None),
    x_app_token: str | None = Header(default=None),
) -> dict:
    _check_token(authorization, x_app_token)
    index = get_fund_index()
    results = index.search(q, limit=max(1, min(limit, 100)))
    return {"query": q, "count": len(results), "funds": results}


@app.get("/api/funds/{isin}")
def get_fund_detail(
    isin: str,
    authorization: str | None = Header(default=None),
    x_app_token: str | None = Header(default=None),
) -> dict:
    _check_token(authorization, x_app_token)
    index = get_fund_index()
    detail = index.get_fund_detail(isin)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Fund with ISIN '{isin}' not found")
    return {"fund": detail}


@app.get("/api/nav/{isin}/history")
def get_nav_history(
    isin: str,
    authorization: str | None = Header(default=None),
    x_app_token: str | None = Header(default=None),
) -> dict:
    _check_token(authorization, x_app_token)
    try:
        data = get_fund_nav_history(isin)
        if not data.get("success"):
            raise HTTPException(status_code=404, detail=data.get("error") or "NAV history not found")
        return data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch NAV history: {exc!s}") from exc


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
    isin = body.isin.strip()
    query_log = new_fund_brief_logger()
    query_log.log_request({"isin": isin})
    article_count = 0
    try:
        result = generate_fund_brief(isin, settings=settings, query_log=query_log)
        article_count = len(result.get("sources") or [])
        insight_source = str(result.get("insight_source") or "")
        if insight_source == "no_articles":
            query_log.log_insight_output(
                insight_source="no_articles",
                char_count=len(result.get("insight_summary") or result.get("insight") or ""),
                preview=str(result.get("insight_summary") or result.get("insight") or ""),
            )
        outcome = "no_articles" if insight_source == "no_articles" else "ok"
        meta = query_log.finish(
            outcome=outcome,
            article_count=article_count,
            insight_source=insight_source,
        )
        _attach_llm_meta(result, meta)
        return result
    except ValueError as exc:
        query_log.log_error("validation", str(exc))
        query_log.finish(outcome="error", article_count=article_count)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        query_log.log_error("runtime", str(exc))
        query_log.finish(outcome="error", article_count=article_count)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        provider = llm_provider(settings)
        query_log.log_error("llm", str(exc))
        query_log.finish(outcome="llm_error", article_count=article_count)
        raise HTTPException(status_code=502, detail=f"{provider} request failed: {exc}") from exc
    except Exception as exc:
        query_log.log_error("unhandled", str(exc))
        query_log.finish(outcome="error", article_count=article_count)
        raise HTTPException(status_code=500, detail=str(exc)[:800]) from exc


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    holdings_map = holdings_archive_available()
    return {
        "ok": True,
        "collection": settings.qdrant_collection,
        "llm_provider": llm_provider(settings),
        "llm_model": llm_model(settings),
        "sector_ranking_index": sector_ranking_data_available(),
        "holdings_archive": holdings_map,
        "embeddings_ready": embeddings_ready(),
        "llm_key_configured": llm_api_key_configured(settings),
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

    reset_llm_request_state()
    query_log = new_query_logger()
    configured_provider = llm_provider(settings)
    query_log.write(
        f"config llm_provider={configured_provider} llm_model={llm_model(settings)} "
        f"collection={settings.qdrant_collection}"
    )
    query_log.note("request_start", llm_provider=configured_provider, llm_model=llm_model(settings))
    query_log.log_request(
        {
            "question": body.question,
            "stock": body.stock,
            "date_from": body.date_from,
            "date_to": body.date_to,
            "min_impact": body.min_impact,
            "source": body.source,
            "direction": body.direction,
            "configured_llm_provider": configured_provider,
            "configured_llm_model": llm_model(settings),
        }
    )

    article_count = 0
    try:
        if not llm_api_key_configured(settings):
            message = missing_llm_key_message(settings)
            query_log.log_error("config", message)
            query_log.finish(outcome="error", article_count=0)
            raise HTTPException(status_code=500, detail=message)

        result = run_ask_engine(
            body.question,
            date_from=body.date_from,
            date_to=body.date_to,
            min_impact=body.min_impact,
            source=body.source,
            direction=body.direction,
            query_log=query_log,
        )
        article_count = len(result.get("sources") or [])
        outcome = str(result.get("outcome") or "ok")
        if result.get("refused"):
            outcome = "refused"
        if result.get("pipeline_errors") and outcome == "ok":
            outcome = "partial"
        meta = query_log.finish(
            outcome=outcome,
            article_count=article_count,
            insight_source=str(result.get("insight_source") or ""),
            extra={
                "question": body.question.strip(),
                "intent": result.get("intent"),
                "sub_queries": result.get("sub_queries"),
                "output_score": result.get("output_score"),
                "pipeline_errors": result.get("pipeline_errors"),
            },
        )
        _attach_llm_meta(result, meta)
        return result
    except httpx.HTTPStatusError as exc:
        provider = llm_provider(get_settings())
        query_log.log_error("llm", str(exc))
        query_log.finish(outcome="llm_error", article_count=article_count)
        if exc.response is not None and exc.response.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini rate limit (HTTP 429). Wait a few minutes, use fund/impact questions "
                    "(no LLM), set DEEPSEEK_API_KEY for fallback, or set RAG_LLM_PROVIDER=deepseek."
                ),
            ) from exc
        raise HTTPException(status_code=502, detail=f"{provider} request failed: {exc}") from exc
    except httpx.HTTPError as exc:
        provider = llm_provider(get_settings())
        query_log.log_error("llm", str(exc))
        query_log.finish(outcome="llm_error", article_count=article_count)
        raise HTTPException(status_code=502, detail=f"{provider} request failed: {exc}") from exc
    except RuntimeError as exc:
        msg = str(exc)
        if "429" in msg or "Gemini" in msg or "quota" in msg.lower():
            query_log.log_error("llm", msg)
            query_log.finish(outcome="llm_error", article_count=article_count)
            raise HTTPException(status_code=503, detail=msg) from exc
        query_log.log_error("unhandled", msg)
        query_log.finish(outcome="error", article_count=article_count)
        raise HTTPException(status_code=500, detail=msg) from exc
    except Exception as exc:
        query_log.log_error("unhandled", str(exc))
        query_log.finish(outcome="error", article_count=article_count)
        raise HTTPException(status_code=500, detail=str(exc)[:800]) from exc
