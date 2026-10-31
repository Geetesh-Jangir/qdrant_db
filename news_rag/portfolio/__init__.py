"""Investor book workspace: fetch, normalize, cache, and project slices for RAG tools."""

from news_rag.portfolio.cache import get_normalized_portfolio
from news_rag.portfolio.project import project_modules

__all__ = ["get_normalized_portfolio", "project_modules"]
