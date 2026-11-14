"""CPI, WPI, IIP, and GDP from the MoSPI eSankhyiki JSON-RPC endpoint.

Bond yields are not in the MoSPI RBI dataset. GST is left to a manual feed.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
from pydantic import BaseModel, Field

from news_pipeline.config import repo_root

MOSPI_URL = "https://mcp.mospi.gov.in/"
TTL_SECONDS = 24 * 60 * 60
SOURCE = "mospi"
# shortcut: walk at most 24 months; raise the cap if a series lags more than two years
_MAX_MONTHS = 24

_lock = threading.Lock()


class MospiError(Exception):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class CPIRecord(BaseModel):
    state: str
    sector: str
    commodity_group: str
    index_value: float
    inflation_rate_yoy: float | None
    month: str
    year: int
    base_year: str
    source: str = "mospi:CPI"
    fetched_at: datetime


class WPIRecord(BaseModel):
    commodity_group: str
    index_value: float
    inflation_rate_yoy: float | None
    yoy_derived: bool = True
    month: str
    year: int
    base_year: str
    source: str = "mospi:WPI"
    fetched_at: datetime


class IIPRecord(BaseModel):
    sector: str
    index_value: float
    growth_rate_yoy: float | None
    month: str
    year: int
    base_year: str
    source: str = "mospi:IIP"
    fetched_at: datetime


class GDPRecord(BaseModel):
    indicator: str
    fiscal_year: str
    quarter: str | None
    value_rs_crore: float
    constant_rs_crore: float | None
    growth_rate_yoy: float | None
    yoy_derived: bool = True
    series: str
    base_year: str
    source: str = "mospi:NAS"
    fetched_at: datetime


class BondYieldResult(BaseModel):
    status: str = "unavailable"
    detail: str = "MoSPI RBI dataset has no G-sec or bond-yield series"
    records: list[dict[str, Any]] = Field(default_factory=list)


class MacroSnapshot(BaseModel):
    cpi: list[CPIRecord] = Field(default_factory=list)
    wpi: list[WPIRecord] = Field(default_factory=list)
    iip: list[IIPRecord] = Field(default_factory=list)
    gdp: list[GDPRecord] = Field(default_factory=list)
    bond_yields: BondYieldResult = Field(default_factory=BondYieldResult)
    as_of: datetime
    unavailable: list[str] = Field(default_factory=list)


def _num(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", ""))
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_dir(path: Path | None) -> Path:
    return path or (repo_root() / "data" / "ai_insight" / "cache" / "mospi")


def _sse_json(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise MospiError("MoSPI response had no SSE data line", retryable=True)


def _payload(rpc: dict[str, Any]) -> dict[str, Any]:
    if "error" in rpc:
        raise MospiError(str(rpc["error"]), retryable=False)
    result = rpc.get("result") or {}
    data = result.get("structuredContent")
    if not data:
        content = result.get("content") or []
        if not content:
            raise MospiError("empty MoSPI result", retryable=True)
        data = json.loads(content[0]["text"])
    if isinstance(data, dict) and data.get("error") and not data.get("data"):
        raise MospiError(str(data.get("hint") or data["error"]), retryable=False)
    return data if isinstance(data, dict) else {"data": data}


class MospiClient:
    def __init__(
        self,
        http: httpx.Client | None = None,
        cache_dir: Path | None = None,
        *,
        ttl_seconds: int = TTL_SECONDS,
        retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._http = http or httpx.Client(timeout=40)
        self._owns_http = http is None
        self.cache_dir = _cache_dir(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.retries = retries
        self._sleep = sleep

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        cached = self._read(tool, args)
        if cached is not None:
            return cached
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                data = self._post(tool, args)
            except MospiError as exc:
                last = exc
                if not exc.retryable or attempt == self.retries - 1:
                    raise
                self._sleep(0.2 * (2**attempt))
                continue
            except httpx.TimeoutException as exc:
                last = exc
                if attempt == self.retries - 1:
                    raise MospiError(str(exc), retryable=True) from exc
                self._sleep(0.2 * (2**attempt))
                continue
            self._write(tool, args, data)
            return data
        raise MospiError(str(last), retryable=True)

    def _post(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        response = self._http.post(
            MOSPI_URL,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}},
        )
        if response.status_code >= 500:
            raise MospiError(f"HTTP {response.status_code}", retryable=True)
        if response.status_code >= 400:
            raise MospiError(f"HTTP {response.status_code}", retryable=False)
        return _payload(_sse_json(response.text))

    def _key(self, tool: str, args: dict[str, Any]) -> Path:
        blob = json.dumps({"tool": tool, "args": args}, sort_keys=True)
        return self.cache_dir / f"{hashlib.sha256(blob.encode()).hexdigest()}.json"

    def _read(self, tool: str, args: dict[str, Any]) -> dict[str, Any] | None:
        path = self._key(tool, args)
        if not path.exists():
            return None
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if time.time() - float(stored.get("cached_at") or 0) >= self.ttl_seconds:
            return None
        return stored.get("data")

    def _write(self, tool: str, args: dict[str, Any], data: dict[str, Any]) -> None:
        path = self._key(tool, args)
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"cached_at": time.time(), "data": data}),
                encoding="utf-8",
            )


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    return data if isinstance(data, list) else []


def _codes(meta: dict[str, Any], key: str) -> list[Any]:
    found: list[Any] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if key in node and not isinstance(node[key], (dict, list)):
                found.append(node[key])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(meta)
    # unique, keep order
    out: list[Any] = []
    for item in found:
        if item not in out:
            out.append(item)
    return out


def _periods(meta: dict[str, Any]) -> list[tuple[int, int]]:
    years = sorted({int(y) for y in _codes(meta, "year") if str(y).isdigit()}, reverse=True)
    months = sorted({int(m) for m in _codes(meta, "month_code") if str(m).isdigit()}, reverse=True)
    if not years:
        years = [_now().year]
    if not months:
        months = list(range(12, 0, -1))
    pairs = [(year, month) for year in years for month in months]
    return pairs[:_MAX_MONTHS]


def _client(client: MospiClient | None) -> MospiClient:
    return client or MospiClient()


def fetch_cpi(client: MospiClient | None = None) -> list[CPIRecord]:
    c = _client(client)
    meta = c.call("get_metadata", {"dataset": "CPI", "base_year": "2024", "level": "Group"})
    fetched = _now()
    for year, month in _periods(meta):
        payload = c.call(
            "get_data",
            {
                "dataset": "CPI",
                "filters": {
                    "base_year": "2024",
                    "series": "Current",
                    "year": str(year),
                    "month_code": str(month),
                },
            },
        )
        picked = []
        for row in _rows(payload):
            if row.get("state") != "All India":
                continue
            group = row.get("division") or row.get("group") or ""
            if group not in ("CPI (General)", "General"):
                continue
            index = _num(row.get("index"))
            if index is None:
                continue
            picked.append(
                CPIRecord(
                    state="All India",
                    sector=str(row.get("sector") or ""),
                    commodity_group=str(group),
                    index_value=index,
                    inflation_rate_yoy=_num(row.get("inflation")),
                    month=str(row.get("month") or month),
                    year=int(row.get("year") or year),
                    base_year="2024",
                    fetched_at=fetched,
                )
            )
        if picked:
            return picked
    return []


def _wpi_yoy(current: float, prior: float | None) -> float | None:
    if prior is None or prior == 0:
        return None
    return round((current / prior - 1) * 100, 2)


def fetch_wpi(client: MospiClient | None = None) -> list[WPIRecord]:
    c = _client(client)
    meta = c.call("get_metadata", {"dataset": "WPI", "base_year": "2022-23"})
    fetched = _now()
    for year, month in _periods(meta):
        payload = c.call(
            "get_data",
            {"dataset": "WPI", "filters": {"base_year": "2022-23", "year": str(year), "month_code": str(month)}},
        )
        heads = [
            row
            for row in _rows(payload)
            if row.get("group") in (None, "") and row.get("item") in (None, "") and row.get("major_group")
        ]
        if not heads:
            continue
        prior = {
            row.get("major_group"): _num(row.get("index_value"))
            for row in _rows(
                c.call(
                    "get_data",
                    {
                        "dataset": "WPI",
                        "filters": {"base_year": "2022-23", "year": str(year - 1), "month_code": str(month)},
                    },
                )
            )
            if row.get("group") in (None, "") and row.get("item") in (None, "")
        }
        out = []
        for row in heads:
            index = _num(row.get("index_value"))
            if index is None:
                continue
            out.append(
                WPIRecord(
                    commodity_group=str(row["major_group"]),
                    index_value=index,
                    inflation_rate_yoy=_wpi_yoy(index, prior.get(row["major_group"])),
                    month=str(row.get("month") or month),
                    year=int(row.get("year") or year),
                    base_year="2022-23",
                    fetched_at=fetched,
                )
            )
        if out:
            return out
    return []


def fetch_iip(client: MospiClient | None = None) -> list[IIPRecord]:
    c = _client(client)
    meta = c.call("get_metadata", {"dataset": "IIP", "base_year": "2011-12", "frequency": "Monthly"})
    fetched = _now()
    for year, month in _periods(meta):
        picked: list[IIPRecord] = []
        for kind in ("General", "Sectoral"):
            payload = c.call(
                "get_data",
                {
                    "dataset": "IIP",
                    "filters": {
                        "base_year": "2011-12",
                        "frequency": "Monthly",
                        "year": str(year),
                        "month_code": str(month),
                        "type": kind,
                    },
                },
            )
            for row in _rows(payload):
                if kind == "Sectoral" and str(row.get("sub_category") or "").strip():
                    continue
                index = _num(row.get("index"))
                if index is None:
                    continue
                picked.append(
                    IIPRecord(
                        sector=str(row.get("category") or kind),
                        index_value=index,
                        growth_rate_yoy=_num(row.get("growth_rate")),
                        month=str(row.get("month") or month),
                        year=int(row.get("year") or year),
                        base_year="2011-12",
                        fetched_at=fetched,
                    )
                )
        if picked:
            return picked
    return []


def _prev_fy(year: str) -> str | None:
    try:
        start = int(str(year)[:4])
    except ValueError:
        return None
    return f"{start - 1}-{str(start)[-2:]}"


def fetch_gdp(client: MospiClient | None = None) -> list[GDPRecord]:
    c = _client(client)
    meta = c.call(
        "get_metadata",
        {"dataset": "NAS", "indicator_code": 5, "base_year": "2022-23", "series": "Current"},
    )
    years = [str(y) for y in _codes(meta, "year") if "-" in str(y)]
    if not years:
        return []
    latest = years[0]
    prior = _prev_fy(latest)
    year_filter = f"{latest},{prior}" if prior else latest
    payload = c.call(
        "get_data",
        {
            "dataset": "NAS",
            "filters": {
                "base_year": "2022-23",
                "series": "Current",
                "frequency_code": "Quarterly",
                "indicator_code": "1,5",
                "year": year_filter,
            },
        },
    )
    rows = _rows(payload)
    by_key = {
        (row.get("indicator"), row.get("year"), row.get("quarter")): _num(row.get("constant_price"))
        for row in rows
    }
    fetched = _now()
    out: list[GDPRecord] = []
    for row in rows:
        if row.get("year") != latest:
            continue
        current = _num(row.get("current_price"))
        if current is None:
            continue
        constant = _num(row.get("constant_price"))
        prev = by_key.get((row.get("indicator"), prior, row.get("quarter")))
        out.append(
            GDPRecord(
                indicator=str(row.get("indicator") or ""),
                fiscal_year=str(latest),
                quarter=str(row["quarter"]) if row.get("quarter") else None,
                value_rs_crore=current,
                constant_rs_crore=constant,
                growth_rate_yoy=_wpi_yoy(constant, prev) if constant is not None else None,
                series="Current",
                base_year="2022-23",
                fetched_at=fetched,
            )
        )
    return out


def fetch_bond_yields() -> BondYieldResult:
    return BondYieldResult()


def get_macro_snapshot(client: MospiClient | None = None) -> MacroSnapshot:
    jobs = {
        "cpi": fetch_cpi,
        "wpi": fetch_wpi,
        "iip": fetch_iip,
        "gdp": fetch_gdp,
    }
    out: dict[str, Any] = {}
    unavailable: list[str] = []

    def _take(name: str, fn) -> None:
        try:
            out[name] = fn(client)
        except Exception as exc:
            out[name] = []
            unavailable.append(f"{name}: {exc}"[:240])

    # httpx.Client is not thread-safe; a shared client runs one dataset at a time.
    if client is not None:
        for name, fn in jobs.items():
            _take(name, fn)
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda item: _take(*item), jobs.items()))
    bond = fetch_bond_yields()
    if bond.status != "ok":
        unavailable.append(f"bond_yields: {bond.detail}")
    return MacroSnapshot(as_of=_now(), unavailable=unavailable, bond_yields=bond, **out)


def write_snapshot(snapshot: MacroSnapshot, root: Path | None = None) -> Path:
    path = (root or repo_root()) / "data" / "ai_insight" / "macro_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path
