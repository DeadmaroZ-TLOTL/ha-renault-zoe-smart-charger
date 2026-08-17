"""Normalize authenticated AMPECO charging-session history."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import re
from typing import Any


def ampeco_history_page(
    payload: Any,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Extract one page and report whether another page should be fetched."""
    if isinstance(payload, list):
        return _mapping_list(payload), len(payload) >= per_page
    if not isinstance(payload, Mapping):
        return [], False

    root: Any = payload.get("data", payload)
    items: Any = root
    if isinstance(root, Mapping):
        for key in ("sessions", "items", "history", "records", "data"):
            if isinstance(root.get(key), list):
                items = root[key]
                break
    records = _mapping_list(items)

    pagination = next(
        (
            value
            for value in (
                payload.get("meta"),
                payload.get("pagination"),
                root.get("meta") if isinstance(root, Mapping) else None,
                root.get("pagination") if isinstance(root, Mapping) else None,
            )
            if isinstance(value, Mapping)
        ),
        {},
    )
    current_page = _as_int(
        _first(pagination, "current_page", "currentPage", "page")
    ) or page
    last_page = _as_int(
        _first(pagination, "last_page", "lastPage", "total_pages", "totalPages")
    )
    if last_page is not None:
        return records, current_page < last_page
    next_value = _first(pagination, "next", "next_page", "nextPage", "next_page_url")
    if next_value is not None:
        return records, bool(next_value)
    total = _as_int(_first(pagination, "total", "total_count", "totalCount"))
    if total is not None:
        return records, page * per_page < total
    return records, len(records) >= per_page


def ampeco_history_location_ids(
    records: list[dict[str, Any]],
) -> list[str]:
    """Return unique AMPECO location IDs referenced by history records."""
    return sorted(
        {
            str(location_id)
            for record in records
            if (
                location_id := _path_first(
                    record,
                    "locationId",
                    "location_id",
                    "session.locationId",
                    "session.location_id",
                )
            )
            is not None
        }
    )


def ampeco_location_lookup(payload: Any) -> dict[str, dict[str, Any]]:
    """Index AMPECO location details returned by the locations endpoint."""
    if not isinstance(payload, Mapping):
        return {}
    locations = payload.get("locations")
    if not isinstance(locations, list):
        return {}
    return {
        str(location["id"]): dict(location)
        for location in locations
        if isinstance(location, Mapping) and location.get("id") is not None
    }


def parse_ampeco_transactions(
    records: list[dict[str, Any]],
    *,
    account_id: str,
    account_name: str,
    account_type: str,
    provider_name: str,
    locations: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Normalize exact completed sessions returned by an AMPECO app account."""
    result: list[dict[str, Any]] = []
    for raw in records:
        start = _datetime_value(
            _path_first(
                raw,
                "startedAt",
                "started_at",
                "startDate",
                "start_date",
                "startTime",
                "start_time",
                "start",
                "session.startedAt",
            )
        )
        end = _datetime_value(
            _path_first(
                raw,
                "stoppedAt",
                "stopped_at",
                "endedAt",
                "ended_at",
                "endDate",
                "end_date",
                "endTime",
                "end_time",
                "end",
                "session.stoppedAt",
            )
        )
        if start is None or end is None:
            continue

        energy_kwh = _energy_kwh(raw)
        cost_eur = _cost_eur(raw)
        duration = _duration_minutes(raw, start, end)
        station = _station_values(raw, locations=locations or {})
        transaction_id = _path_first(
            raw,
            "id",
            "sessionId",
            "session_id",
            "transactionId",
            "transaction_id",
            "session.id",
        )
        status = _path_first(raw, "status", "state", "session.status")
        currency = _path_first(
            raw,
            "currency",
            "currencyCode",
            "currency_code",
            "price.currency",
            "transaction.currency",
            "session.currency.code",
        )
        rate = (
            round(cost_eur / energy_kwh * 100.0, 3)
            if cost_eur is not None and energy_kwh and energy_kwh > 0
            else None
        )
        result.append(
            {
                "transaction_id": str(transaction_id) if transaction_id else None,
                "source_page": f"{account_type}_app",
                "source_account_type": account_type,
                "account_id": account_id,
                "account_name": account_name,
                "provider": provider_name,
                "operator": provider_name,
                "station_id": station["station_id"],
                "station_name": station["station_name"],
                "station_address": station["station_address"],
                "connector_code": station["connector_code"],
                "start": start,
                "end": end,
                "duration_minutes": duration,
                "energy_kwh": energy_kwh,
                "cost_eur": cost_eur,
                "total_cost_eur": cost_eur,
                "total_rate_c_per_kwh": rate,
                "currency": str(currency or "EUR").upper(),
                "transaction_status": str(status or "completed"),
                "receipt_url": _text(
                    _path_first(raw, "receiptUrl", "session.receiptUrl")
                ),
                "price_source": f"{account_type}_app",
                "provider_reported_cost": cost_eur is not None,
                "provider_reported_energy": energy_kwh is not None,
            }
        )
    return sorted(result, key=lambda item: item["end"], reverse=True)


def _energy_kwh(record: Mapping[str, Any]) -> float | None:
    for path in (
        "energyKwh",
        "energy_kwh",
        "consumedEnergyKwh",
        "consumed_energy_kwh",
        "energy.kwh",
        "energy.kWh",
        "consumption.kwh",
    ):
        value = _number(_path(record, path))
        if value is not None:
            return round(max(0.0, value), 3)
    for path in (
        "energyWh",
        "energy_wh",
        "energyConsumedWh",
        "energy_consumed_wh",
        "energy.wh",
        "consumption.wh",
    ):
        value = _number(_path(record, path))
        if value is not None:
            return round(max(0.0, value) / 1000.0, 3)

    value = _path_first(
        record,
        "energyConsumed",
        "energy_consumed",
        "consumedEnergy",
        "consumed_energy",
        "chargedEnergy",
        "charged_energy",
        "totalEnergy",
        "total_energy",
        "energy",
        "consumption",
        "session.energy",
    )
    number, unit = _quantity(value)
    if number is None:
        return None
    if unit.casefold() in {"wh", "watt-hour", "watt-hours"}:
        number /= 1000.0
    elif not unit and number > 500:
        number /= 1000.0
    return round(max(0.0, number), 3)


def _cost_eur(record: Mapping[str, Any]) -> float | None:
    for path in (
        "amountCents",
        "amount_cents",
        "costCents",
        "cost_cents",
        "totalPriceCents",
        "total_price_cents",
    ):
        value = _number(_path(record, path))
        if value is not None:
            return round(value / 100.0, 4)
    value = _path_first(
        record,
        "totalPrice",
        "total_price",
        "totalAmount",
        "total_amount",
        "finalPrice",
        "final_price",
        "cost",
        "amount",
        "price.total",
        "price.amount",
        "transaction.totalAmount",
        "transaction.amount",
        "payment.amount",
        "session.totalAmount",
    )
    number, unit = _quantity(value, prefer_tax_total=True)
    if number is None:
        return None
    if unit.casefold() in {"cent", "cents", "ct"}:
        number /= 100.0
    return round(max(0.0, number), 4)


def _station_values(
    record: Mapping[str, Any],
    *,
    locations: Mapping[str, Mapping[str, Any]],
) -> dict[str, str | None]:
    location = _path_first(record, "location", "station", "session.location")
    location = location if isinstance(location, Mapping) else {}
    station_id = _text(
        _first(location, "id", "locationId", "location_id")
        or _path_first(
            record,
            "locationId",
            "location_id",
            "stationId",
            "session.locationId",
            "session.location_id",
        )
    )
    location_detail = locations.get(station_id or "", {})
    evse = _path_first(record, "evse", "connector", "session.evse")
    evse = evse if isinstance(evse, Mapping) else {}
    address_value = _first(
        location,
        "address",
        "fullAddress",
        "full_address",
        "streetAddress",
    ) or _path_first(record, "stationAddress", "station_address", "address")
    if not address_value:
        address_value = _first(
            location_detail,
            "address",
            "fullAddress",
            "full_address",
            "streetAddress",
        )
    if isinstance(address_value, list):
        address_value = ", ".join(str(item) for item in address_value if item)
    return {
        "station_id": station_id,
        "station_name": _text(
            _first(location, "name", "title")
            or _path_first(record, "stationName", "station_name", "locationName")
            or _first(location_detail, "name", "title")
        ),
        "station_address": _text(address_value),
        "connector_code": _text(
            _first(evse, "emi3Identifier", "roamingEvseId", "identifier", "id")
            or _path_first(
                record,
                "evseId",
                "evse_id",
                "connectorId",
                "connector_id",
            )
        ),
    }


def _duration_minutes(record: Mapping[str, Any], start: str, end: str) -> int:
    value = _path_first(
        record,
        "durationMinutes",
        "duration_minutes",
        "durationMin",
        "duration_min",
    )
    number, unit = _quantity(value)
    if number is not None:
        if unit.casefold() in {"s", "sec", "second", "seconds"}:
            number /= 60.0
        elif unit.casefold() in {"h", "hour", "hours"}:
            number *= 60.0
        return max(0, round(number))

    seconds = _path_first(
        record,
        "durationSeconds",
        "duration_seconds",
        "durationInSeconds",
        "duration_in_seconds",
        "session.duration",
        "session.totalDuration",
    )
    second_number, second_unit = _quantity(seconds)
    if second_number is not None:
        if second_unit.casefold() in {"m", "min", "minute", "minutes"}:
            return max(0, round(second_number))
        if second_unit.casefold() in {"h", "hour", "hours"}:
            second_number *= 3600.0
        return max(0, round(second_number / 60.0))

    value = _path_first(record, "duration")
    number, unit = _quantity(value)
    if number is not None:
        if unit.casefold() in {"s", "sec", "second", "seconds"}:
            number /= 60.0
        elif unit.casefold() in {"h", "hour", "hours"}:
            number *= 60.0
        return max(0, round(number))
    start_time = datetime.fromisoformat(start)
    end_time = datetime.fromisoformat(end)
    return max(0, round((end_time - start_time).total_seconds() / 60.0))


def _quantity(
    value: Any,
    *,
    prefer_tax_total: bool = False,
) -> tuple[float | None, str]:
    unit = ""
    if isinstance(value, Mapping):
        unit = str(_first(value, "unit", "unitName", "currency") or "")
        keys = (
            ("withTax", "with_tax", "total", "value", "amount")
            if prefer_tax_total
            else ("kwh", "kWh", "wh", "value", "amount", "total")
        )
        for key in keys:
            if key not in value:
                continue
            number = _number(value[key])
            if number is not None:
                if not unit and key.casefold() in {"kwh", "wh"}:
                    unit = key
                return number, unit
        return None, unit
    if isinstance(value, str):
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", value.replace(" ", ""))
        if not match:
            return None, ""
        number = _number(match.group(0))
        suffix = value[match.end() :].strip().split(" ", 1)[0]
        return number, suffix
    return _number(value), unit


def _datetime_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        try:
            return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return _datetime_value(int(text))
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _path_first(record: Mapping[str, Any], *paths: str) -> Any:
    for path in paths:
        value = _path(record, path)
        if value is not None and value != "":
            return value
    return None


def _path(record: Mapping[str, Any], path: str) -> Any:
    value: Any = record
    for key in path.split("."):
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _first(record: Mapping[str, Any], *keys: str) -> Any:
    return _path_first(record, *keys)


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _number(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.strip().replace(" ", "").replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
