"""Typed errors for investor portfolio workspace fetch."""

from __future__ import annotations


class PortfolioError(Exception):
    code: str = "portfolio_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class PortfolioNotConfigured(PortfolioError):
    code = "not_configured"


class PortfolioUnavailable(PortfolioError):
    code = "unavailable"


class PortfolioUpstreamError(PortfolioError):
    code = "upstream_error"
