"""Pure helpers for charging-account transaction data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
import re
import unicodedata
from typing import Any


ELEKTRUM_SOURCE = "elektrum_drive"
MOBILLY_SOURCE = "mobilly"
_ELEKTRUM_MATCH_SECONDS = 20 * 60


def parse_elektrum_transactions(
    payload: Mapping[str, Any],
    *,
    account_id: str,
    account_name: str,
) -> list[dict[str, Any]]:
    """Normalize completed Elektrum Drive charging transactions."""
    raw_data = payload.get("data", [])
    if isinstance(raw_data, Mapping):
        raw_data = raw_data.get("transactions", raw_data.get("items", []))
    if not isinstance(raw_data, list):
        return []

    result: list[dict[str, Any]] = []
    for raw in raw_data:
        if not isinstance(raw, Mapping):
            continue
        item = raw.get("item")
        if not isinstance(item, Mapping):
            continue
        if _as_int(raw.get("status")) != 2:
            continue
        start = _timestamp_iso(item.get("startedAt"))
        end = _timestamp_iso(item.get("endedAt"))
        if start is None or end is None:
            continue

        energy_wh = _as_float(item.get("energyUsed"))
        energy_kwh = (
            round(energy_wh / 1000.0, 3)
            if energy_wh is not None and energy_wh >= 0
            else None
        )
        amount_cents = _as_float(raw.get("amount"))
        cost_eur = (
            round(amount_cents / 100.0, 4)
            if amount_cents is not None
            else None
        )
        transaction_id = str(raw.get("id") or "") or None
        rate = (
            round(cost_eur / energy_kwh * 100.0, 3)
            if cost_eur is not None and energy_kwh and energy_kwh > 0
            else None
        )
        result.append(
            {
                "transaction_id": transaction_id,
                "source_page": "elektrum_drive_app",
                "source_account_type": ELEKTRUM_SOURCE,
                "account_id": account_id,
                "account_name": account_name,
                "provider": "Elektrum Drive",
                "operator": "Elektrum Drive",
                "station_name": item.get("stationName"),
                "station_address": item.get("stationAddress"),
                "start": start,
                "end": end,
                "duration_minutes": _duration_minutes(item, start, end),
                "energy_kwh": energy_kwh,
                "cost_eur": cost_eur,
                "total_cost_eur": cost_eur,
                "total_rate_c_per_kwh": rate,
                "tariff_charging_price_c_per_kwh": _as_float(
                    item.get("tariffChargingPriceFull")
                ),
                "tariff_charging_unit": item.get("tariffChargingUnit"),
                "tariff_connection_price_cents": _as_float(
                    item.get("tariffConnectionPriceFull")
                ),
                "tariff_connection_unit": item.get("tariffConnectionUnit"),
                "transaction_status": _transaction_status(raw.get("status")),
                "transaction_type": raw.get("type"),
                "invoice_available": raw.get("invoiceAvailable"),
                "price_source": "elektrum_drive_app",
                "elektrum_transaction": True,
                "provider_reported_cost": cost_eur is not None,
                "provider_reported_energy": energy_kwh is not None,
            }
        )
    return sorted(result, key=lambda record: record["end"], reverse=True)


def tag_account_transactions(
    records: Iterable[Mapping[str, Any]],
    *,
    account_id: str,
    account_name: str,
    account_type: str,
) -> list[dict[str, Any]]:
    """Attach a non-secret account reference to normalized transactions."""
    result = []
    for raw in records:
        record = dict(raw)
        record["account_id"] = account_id
        record["account_name"] = account_name
        record["source_account_type"] = account_type
        result.append(record)
    return result


def merge_account_transactions(
    *record_groups: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge all accounts and prefer exact Elektrum app records on overlap."""
    records = [dict(item) for group in record_groups for item in group]
    records = _deduplicate_same_source(records)

    elektrum = [
        record
        for record in records
        if record.get("source_account_type") == ELEKTRUM_SOURCE
    ]
    consumed_mobilly: set[int] = set()
    for primary in elektrum:
        candidates = [
            (index, candidate)
            for index, candidate in enumerate(records)
            if index not in consumed_mobilly
            and candidate.get("source_account_type") == MOBILLY_SOURCE
            and candidate.get("elektrum_transaction")
            and _same_charge(primary, candidate)
        ]
        if not candidates:
            continue
        index, alternate = min(
            candidates,
            key=lambda pair: _interval_distance(primary, pair[1]),
        )
        consumed_mobilly.add(index)
        _attach_alternate(primary, alternate)

    merged = [
        record
        for index, record in enumerate(records)
        if index not in consumed_mobilly
    ]
    return sorted(merged, key=lambda record: record.get("end") or "", reverse=True)


def apply_provider_transactions(
    sessions: Iterable[Mapping[str, Any]],
    transactions: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply exact provider energy and cost to matching Renault sessions.

    Renault can split one physical charge into several API rows. When that
    happens, the exact provider totals are allocated proportionally while the
    sum remains equal to the provider transaction.
    """
    result = [dict(session) for session in sessions]
    assigned: set[int] = set()
    provider_records = sorted(
        (dict(item) for item in transactions),
        key=lambda item: item.get("end") or "",
    )
    for transaction in provider_records:
        candidates = [
            index
            for index, session in enumerate(result)
            if index not in assigned and _interval_matches(session, transaction)
        ]
        if not candidates:
            continue

        weights = [_session_weight(result[index]) for index in candidates]
        total_weight = sum(weights)
        if total_weight <= 0:
            weights = [1.0] * len(candidates)
            total_weight = float(len(candidates))

        exact_energy = _as_float(transaction.get("energy_kwh"))
        exact_cost = _as_float(
            transaction.get("total_cost_eur", transaction.get("cost_eur"))
        )
        exact_rate = (
            exact_cost / exact_energy * 100.0
            if exact_cost is not None and exact_energy and exact_energy > 0
            else _as_float(transaction.get("total_rate_c_per_kwh"))
        )
        allocated_energy_total = 0.0
        allocated_cost_total = 0.0
        for position, index in enumerate(candidates):
            fraction = weights[position] / total_weight
            session = result[index]
            is_last = position == len(candidates) - 1
            allocated_energy = None
            if exact_energy is not None:
                allocated_energy = round(
                    exact_energy - allocated_energy_total
                    if is_last
                    else exact_energy * fraction,
                    3,
                )
                allocated_energy_total += allocated_energy
            allocated_cost = None
            if exact_cost is not None:
                allocated_cost = round(
                    exact_cost - allocated_cost_total
                    if is_last
                    else exact_cost * fraction,
                    4,
                )
                allocated_cost_total += allocated_cost
            if allocated_energy is not None:
                session["grid_energy_kwh"] = allocated_energy
                session["energy_source"] = "provider_meter"
            if allocated_cost is not None:
                session["total_cost_eur"] = allocated_cost
                session["spot_cost_eur"] = None
                session["delivery_cost_eur"] = None
            if exact_rate is not None:
                session["total_rate_c_per_kwh"] = round(exact_rate, 3)
            session.update(
                {
                    "price_source": transaction.get("price_source"),
                    "price_entity": (
                        "sensor.renault_zoe_new_charging_accounts"
                    ),
                    "price_coverage_percent": 100.0,
                    "station_name": transaction.get("station_name")
                    or transaction.get("provider"),
                    "station_address": transaction.get("station_address"),
                    "provider": transaction.get("provider"),
                    "provider_transaction_id": transaction.get(
                        "transaction_id"
                    ),
                    "provider_account_id": transaction.get("account_id"),
                    "provider_account_name": transaction.get("account_name"),
                    "provider_reported_cost": transaction.get(
                        "provider_reported_cost", exact_cost is not None
                    ),
                    "provider_reported_energy": transaction.get(
                        "provider_reported_energy", exact_energy is not None
                    ),
                    "provider_total_grid_energy_kwh": exact_energy,
                    "provider_total_cost_eur": exact_cost,
                    "provider_allocation_fraction": round(fraction, 6),
                    "provider_split_session_count": len(candidates),
                    "transaction_status": transaction.get(
                        "transaction_status"
                    ),
                    "alternate_sources": transaction.get(
                        "alternate_sources", []
                    ),
                }
            )
            assigned.add(index)
    return result


def _deduplicate_same_source(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    keys: dict[tuple[Any, ...], int] = {}
    for record in records:
        source = record.get("source_account_type") or record.get("price_source")
        transaction_id = record.get("transaction_id")
        if transaction_id:
            # Mobilly IDs are account-local. The interval distinguishes equal
            # numeric IDs while still collapsing a genuinely shared charge.
            key = (
                source,
                "id",
                str(transaction_id),
                record.get("start"),
                record.get("end"),
            )
        else:
            key = (
                source,
                _normalize(record.get("provider")),
                record.get("start"),
                record.get("end"),
                _as_float(record.get("energy_kwh")),
                _as_float(record.get("total_cost_eur")),
            )
        existing_index = keys.get(key)
        if existing_index is None:
            keys[key] = len(result)
            result.append(record)
            continue
        _attach_alternate(result[existing_index], record)
    return result


def _same_charge(primary: Mapping[str, Any], alternate: Mapping[str, Any]) -> bool:
    primary_start = _parse_datetime(primary.get("start"))
    primary_end = _parse_datetime(primary.get("end"))
    alternate_start = _parse_datetime(alternate.get("start"))
    alternate_end = _parse_datetime(alternate.get("end"))
    if None in {primary_start, primary_end, alternate_start, alternate_end}:
        return False
    if abs((primary_start - alternate_start).total_seconds()) > _ELEKTRUM_MATCH_SECONDS:
        return False
    if abs((primary_end - alternate_end).total_seconds()) > _ELEKTRUM_MATCH_SECONDS:
        return False

    primary_energy = _as_float(primary.get("energy_kwh"))
    alternate_energy = _as_float(alternate.get("energy_kwh"))
    if primary_energy is None or alternate_energy is None:
        return True
    tolerance = max(2.0, primary_energy * 0.2)
    return abs(primary_energy - alternate_energy) <= tolerance


def _interval_matches(
    session: Mapping[str, Any], transaction: Mapping[str, Any]
) -> bool:
    session_start = _parse_datetime(session.get("start"))
    session_end = _parse_datetime(session.get("end"))
    transaction_start = _parse_datetime(transaction.get("start"))
    transaction_end = _parse_datetime(transaction.get("end"))
    if None in {session_start, session_end, transaction_start, transaction_end}:
        return False
    margin = timedelta(seconds=_ELEKTRUM_MATCH_SECONDS)
    return (
        session_start <= transaction_end + margin
        and session_end >= transaction_start - margin
    )


def _session_weight(session: Mapping[str, Any]) -> float:
    for key in (
        "grid_energy_kwh",
        "energy_recovered_kwh",
        "estimated_battery_energy_kwh",
    ):
        value = _as_float(session.get(key))
        if value is not None and value > 0:
            return value
    start = _parse_datetime(session.get("start"))
    end = _parse_datetime(session.get("end"))
    if start is not None and end is not None:
        return max(1.0, (end - start).total_seconds())
    return 1.0


def _interval_distance(
    primary: Mapping[str, Any], alternate: Mapping[str, Any]
) -> float:
    distance = 0.0
    for key in ("start", "end"):
        primary_time = _parse_datetime(primary.get(key))
        alternate_time = _parse_datetime(alternate.get(key))
        if primary_time is None or alternate_time is None:
            return float("inf")
        distance += abs((primary_time - alternate_time).total_seconds())
    return distance


def _attach_alternate(
    primary: dict[str, Any], alternate: Mapping[str, Any]
) -> None:
    references = list(primary.get("alternate_sources") or [])
    reference = {
        "price_source": alternate.get("price_source"),
        "account_id": alternate.get("account_id"),
        "account_name": alternate.get("account_name"),
        "transaction_id": alternate.get("transaction_id"),
    }
    if reference not in references:
        references.append(reference)
    primary["alternate_sources"] = references

    if primary.get("energy_kwh") is None and alternate.get("energy_kwh") is not None:
        primary["energy_kwh"] = alternate.get("energy_kwh")
        primary["provider_reported_energy"] = alternate.get(
            "provider_reported_energy", True
        )
    if (
        primary.get("total_cost_eur") is None
        and alternate.get("total_cost_eur") is not None
    ):
        primary["cost_eur"] = alternate.get("cost_eur")
        primary["total_cost_eur"] = alternate.get("total_cost_eur")
        primary["provider_reported_cost"] = alternate.get(
            "provider_reported_cost", True
        )


def _timestamp_iso(value: Any) -> str | None:
    timestamp = _as_float(value)
    if timestamp is None or timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _duration_minutes(
    item: Mapping[str, Any], start: str, end: str
) -> int:
    duration = _as_float(item.get("duration"))
    if duration is not None and duration >= 0:
        return round(duration)
    start_time = _parse_datetime(start)
    end_time = _parse_datetime(end)
    if start_time is None or end_time is None:
        return 0
    return max(0, round((end_time - start_time).total_seconds() / 60))


def _transaction_status(value: Any) -> str:
    try:
        return {1: "pending", 2: "success", 3: "failed"}.get(int(value), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
