"""Governed Frankfurter v2 currency conversion using Decimal arithmetic."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

from brain.runtime.external.config import frankfurter_enabled
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.models import ExternalAPIRequest

FRANKFURTER_API_ID = "frankfurter"
CURRENCY_TOOL_NAME = "currency_convert"
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_MAX_AMOUNT = Decimal("1000000000000")


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True, slots=True)
class CurrencyConvertInput:
    amount: str | int | Decimal
    from_currency: str
    to_currency: str

    def normalized(self) -> tuple[Decimal, str, str]:
        if isinstance(self.amount, (bool, float)):
            raise ValueError("invalid_amount")
        try:
            amount = Decimal(self.amount)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("invalid_amount") from None
        base = str(self.from_currency or "").strip().upper()
        quote = str(self.to_currency or "").strip().upper()
        if not amount.is_finite() or not Decimal(0) < amount <= _MAX_AMOUNT:
            raise ValueError("invalid_amount")
        if not _CURRENCY.fullmatch(base) or not _CURRENCY.fullmatch(quote):
            raise ValueError("invalid_currency")
        return amount, base, quote


@dataclass(frozen=True, slots=True)
class CurrencyConvertResult:
    amount: str
    base: str
    quote: str
    rate: str
    converted_amount: str
    rate_date: str
    provider: str
    provenance: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _result(
    amount: Decimal,
    base: str,
    quote: str,
    rate: Decimal,
    rate_date: str,
    provenance: dict[str, object],
    provider: str = "Frankfurter",
) -> CurrencyConvertResult:
    converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return CurrencyConvertResult(
        _decimal_text(amount),
        base,
        quote,
        _decimal_text(rate),
        _decimal_text(converted),
        rate_date,
        provider,
        provenance,
    )


def convert_currency(
    value: CurrencyConvertInput,
    *,
    gateway: ExternalAPIGateway,
    global_enabled: bool | None = None,
    provider_enabled: bool | None = None,
    event_sink: EventSink | None = None,
) -> CurrencyConvertResult:
    amount, base, quote = value.normalized()
    effective_provider_enabled = (
        frankfurter_enabled() if provider_enabled is None else provider_enabled
    )
    if base == quote:
        gateway.require_feature_gates(
            api_id=FRANKFURTER_API_ID,
            global_enabled=global_enabled,
            provider_enabled=effective_provider_enabled,
            event_sink=event_sink,
        )
        return _result(
            amount,
            base,
            quote,
            Decimal(1),
            "local",
            {
                "source_type": "local_compute",
                "provider": "local",
                "cached": False,
                "freshness": "local_identity",
            },
            provider="local",
        )
    response = gateway.execute(
        ExternalAPIRequest(
            api_id=FRANKFURTER_API_ID,
            method="GET",
            path="/v2/rates",
            query={"base": base, "quotes": quote},
        ),
        global_enabled=global_enabled,
        provider_enabled=effective_provider_enabled,
        event_sink=event_sink,
    )
    rows = response.data
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ExternalGatewayError("provider_schema_error")
    row = rows[0]
    if row.get("base") != base or row.get("quote") != quote:
        raise ExternalGatewayError("provider_schema_error")
    try:
        rate = Decimal(str(row["rate"]))
        rate_day = date.fromisoformat(row["date"])
    except (KeyError, InvalidOperation, TypeError, ValueError):
        raise ExternalGatewayError("provider_schema_error") from None
    if not rate.is_finite() or rate <= 0:
        raise ExternalGatewayError("provider_schema_error")
    if not 1999 <= rate_day.year <= date.today().year + 1:
        raise ExternalGatewayError("provider_schema_error")
    return _result(amount, base, quote, rate, row["date"], dict(response.provenance))
