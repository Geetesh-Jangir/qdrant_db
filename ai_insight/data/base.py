"""One numeric fact per macro entity per date."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class NumericRecord:
    entity: str
    date: str
    value: float | None
    change_pct: float | None
    unit: str
    source: str
    status: str
    detail: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def unavailable(entity: str, source: str, detail: str) -> NumericRecord:
    return NumericRecord(entity, "", None, None, "", source, "unavailable", detail)


@dataclass
class FlowLeg:
    category: str
    buy_inr_crore: float
    sell_inr_crore: float
    net_inr_crore: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class FiiDiiSnapshot:
    trade_date: str
    fii: FlowLeg | None
    dii: FlowLeg | None
    source: str
    status: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "trade_date": self.trade_date,
            "fii": self.fii.as_dict() if self.fii else None,
            "dii": self.dii.as_dict() if self.dii else None,
            "source": self.source,
            "status": self.status,
            "detail": self.detail,
        }
