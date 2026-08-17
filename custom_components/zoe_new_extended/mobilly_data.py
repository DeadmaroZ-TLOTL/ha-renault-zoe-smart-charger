"""Pure helpers for Mobilly charging-station and session data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
import re
import unicodedata
from typing import Any
from zoneinfo import ZoneInfo


ELEKTRUM_MARKERS = frozenset({"elektrum", "elektrumdrive", "latvenergo"})
RIGA = ZoneInfo("Europe/Riga")

_OPERATOR_FIELDS = frozenset(
    {
        "brand",
        "chargepointoperator",
        "cpo",
        "merchant",
        "name",
        "network",
        "operator",
        "owner",
        "partner",
        "provider",
        "site",
        "station",
        "title",
    }
)


class _HtmlTableParser(HTMLParser):
    """Collect plain text cells from HTML tables without extra dependencies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._rows = []
        elif self._table_depth == 1 and tag == "tr":
            self._row = []
        elif self._table_depth == 1 and tag in {"td", "th"}:
            self._cell_parts = []
        elif self._cell_parts is not None and tag == "br":
            self._cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._table_depth == 1 and tag in {"td", "th"}:
            if self._row is not None and self._cell_parts is not None:
                self._row.append(_clean_text(" ".join(self._cell_parts)))
            self._cell_parts = None
        elif self._table_depth == 1 and tag == "tr":
            if self._rows is not None and self._row:
                self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            if self._table_depth == 1 and self._rows is not None:
                self.tables.append(self._rows)
                self._rows = None
            self._table_depth -= 1


def parse_transactions_page(
    page: str,
    *,
    source_page: str,
) -> list[dict[str, Any]]:
    """Parse either Mobilly statement table into normalized EV transactions."""
    parser = _HtmlTableParser()
    parser.feed(page)
    for table in parser.tables:
        parsed = _parse_transaction_table(table, source_page)
        if parsed is not None:
            return parsed
    return []


def parse_app_transactions(
    payload: Mapping[str, Any],
    *,
    source_page: str = "mobilly_app_transactions",
) -> list[dict[str, Any]]:
    """Normalize EV transactions returned by Mobilly's Android API."""
    raw_records = _find_record_list(
        payload,
        ("transactions", "transactionHistory", "history"),
    )
    parsed = []
    for item in raw_records:
        record = _parse_app_record(item, source_page=source_page)
        if record is not None:
            parsed.append(record)
    return parsed


def parse_app_charge_sessions(
    payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Normalize the richer Mobilly EV-session response when available."""
    raw_records = _find_record_list(
        payload,
        ("sessions", "chargeSessions", "chargingSessions"),
        allow_data_list=True,
    )
    parsed = []
    for item in raw_records:
        record = _parse_app_record(
            item,
            source_page="mobilly_app_charge_sessions",
            require_ev_marker=False,
        )
        if record is not None:
            parsed.append(record)
    return parsed


def merge_app_transactions(
    history: Iterable[Mapping[str, Any]],
    sessions: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich app-history rows with exact EV-session end, energy, and station."""
    history_records = [dict(item) for item in history]
    session_records = [dict(item) for item in sessions]
    consumed: set[int] = set()
    enriched = []
    for transaction in history_records:
        candidates = [
            (index, session)
            for index, session in enumerate(session_records)
            if index not in consumed and _app_records_match(transaction, session)
        ]
        if not candidates:
            enriched.append(transaction)
            continue
        index, session = min(
            candidates,
            key=lambda pair: _app_record_distance(transaction, pair[1]),
        )
        consumed.add(index)
        merged = dict(transaction)
        for key in (
            "start",
            "end",
            "duration_minutes",
            "energy_kwh",
            "station_name",
            "station_address",
            "provider",
            "operator",
            "connector_code",
            "transaction_status",
        ):
            if session.get(key) not in (None, ""):
                merged[key] = session[key]
        merged["end_inferred"] = bool(session.get("end_inferred", False))
        merged["session_id"] = session.get("session_id") or session.get(
            "transaction_id"
        )
        enriched.append(merged)

    enriched.extend(
        session
        for index, session in enumerate(session_records)
        if index not in consumed
    )
    return merge_transactions(enriched)


def merge_transactions(
    *record_groups: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge both Mobilly statements, commission rows, and duplicate sessions."""
    raw_records = [dict(item) for group in record_groups for item in group]
    records = raw_records
    base_records = [item for item in records if not item.get("is_commission")]
    commission_records = [item for item in records if item.get("is_commission")]

    for commission in commission_records:
        reference = _best_commission_reference(commission, base_records)
        if reference is None:
            continue
        amount = _as_float(commission.get("cost_eur")) or 0.0
        reference["commission_cost_eur"] = round(
            (_as_float(reference.get("commission_cost_eur")) or 0.0) + amount,
            4,
        )
        reference.setdefault("commission_transaction_ids", []).append(
            commission.get("transaction_id")
        )

    merged: dict[tuple[str | None, str | None, str], dict[str, Any]] = {}
    for record in base_records:
        key = (
            record.get("start"),
            record.get("end"),
            _normalize(record.get("provider")),
        )
        current_key = key if key in merged else next(
            (
                candidate_key
                for candidate_key, candidate in merged.items()
                if _mobilly_records_match(candidate, record)
            ),
            None,
        )
        current = merged.get(current_key) if current_key is not None else None
        if current is None:
            merged[key] = dict(record)
            continue
        merged[current_key] = _merge_duplicate(current, record)

    result = []
    for record in merged.values():
        base_cost = _as_float(record.get("cost_eur"))
        commission_cost = _as_float(record.get("commission_cost_eur")) or 0.0
        total_cost = (
            round(base_cost + commission_cost, 4)
            if base_cost is not None
            else None
        )
        energy = _as_float(record.get("energy_kwh"))
        record["total_cost_eur"] = total_cost
        record["total_rate_c_per_kwh"] = (
            round(total_cost / energy * 100.0, 3)
            if total_cost is not None and energy is not None and energy > 0
            else None
        )
        record["price_source"] = "mobilly"
        record["elektrum_transaction"] = _is_elektrum_record(record)
        record["provider_reported_cost"] = total_cost is not None
        record["provider_reported_energy"] = energy is not None and energy > 0
        result.append(record)
    return sorted(result, key=lambda item: item.get("end") or "", reverse=True)


def merge_cached_app_history(
    fresh: Iterable[Mapping[str, Any]],
    cached: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Keep rich app fields during a partial web-only Mobilly refresh.

    Fresh web statement prices remain authoritative. Cached app rows only
    backfill missing session data, so commissions and costs cannot accumulate
    again on every coordinator refresh.
    """
    result = [dict(item) for item in fresh]
    cached_records = [dict(item) for item in cached]
    consumed: set[int] = set()
    for record in result:
        candidates = [
            (index, candidate)
            for index, candidate in enumerate(cached_records)
            if index not in consumed and _cached_records_match(record, candidate)
        ]
        if not candidates:
            continue
        index, cached_record = min(
            candidates,
            key=lambda pair: _app_record_distance(record, pair[1]),
        )
        consumed.add(index)
        _backfill_cached_app_fields(record, cached_record)

    result.extend(
        record
        for index, record in enumerate(cached_records)
        if index not in consumed
    )
    return sorted(result, key=lambda item: item.get("end") or "", reverse=True)


def is_elektrum_station(record: Mapping[str, Any]) -> bool:
    """Return whether a Mobilly record belongs to Elektrum Drive."""
    return any(
        marker in value
        for value in _operator_values(record)
        for marker in ELEKTRUM_MARKERS
    )


def without_elektrum(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Copy Mobilly records while removing every Elektrum Drive entry."""
    return [dict(record) for record in records if not _is_elektrum_record(record)]


def _parse_transaction_table(
    rows: list[list[str]], source_page: str
) -> list[dict[str, Any]] | None:
    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if "id" in {_normalize_header(item) for item in row}
            and "cenaeur" in {_normalize_header(item) for item in row}
        ),
        None,
    )
    if header_index is None:
        return None

    headers = [_normalize_header(item) for item in rows[header_index]]
    parsed: list[dict[str, Any]] = []
    for row in rows[header_index + 1 :]:
        if not row or _normalize(row[0]).startswith("kopaapmaksats"):
            continue
        values = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
        }
        service = values.get("pakalpojums", "")
        normalized_service = _normalize(service)
        is_commission = normalized_service.startswith("komisijaladejotauto")
        if "elektroautouzlade" not in normalized_service and not is_commission:
            continue

        if source_page == "payments_mobile":
            start, end = _parse_mobile_interval(values.get("darijumalaiks", ""))
        else:
            start, end = _parse_direct_interval(
                values.get("darijumalaiks", ""),
                values.get("laiks", ""),
            )
        if start is None or end is None:
            continue

        amount = values.get("apjoms", "")
        energy = _parse_energy(amount) or _parse_energy(service)
        parsed.append(
            {
                "transaction_id": values.get("id") or None,
                "source_page": source_page,
                "provider": values.get("pakalpojumusniedzejs") or None,
                "operator": values.get("pakalpojumusniedzejs") or None,
                "service": service or None,
                "vehicle": values.get("auto") or None,
                "rfid": values.get("rfidkarte") or None,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "energy_kwh": round(energy, 3) if energy is not None else None,
                "amount_text": amount or None,
                "cost_eur": _parse_decimal(values.get("cenaeur")),
                "vat_eur": _parse_decimal(values.get("pvnsummaeur")),
                "is_commission": is_commission,
            }
        )
    return parsed


def _parse_app_record(
    item: Mapping[str, Any],
    *,
    source_page: str,
    require_ev_marker: bool = True,
) -> dict[str, Any] | None:
    service_type = _display_text(
        _first_nested(item, "type", "transactionType", "serviceType")
    )
    service = _display_text(
        _first_nested(item, "serviceName", "service", "description")
    )
    service_code = _display_text(
        _first_nested(item, "serviceCode", "serviceId", "serviceGroup")
    )
    marker = _normalize(" ".join((service_type, service, service_code)))
    if require_ev_marker and not any(
        value in marker
        for value in ("evcharging", "evcharge", "electriccar", "elektroauto")
    ):
        return None

    start = _parse_app_timestamp(
        _first_nested(
            item,
            "startTime",
            "startedAt",
            "startDate",
            "transactionTime",
            "createdAt",
            "date",
            "time",
        )
    )
    if start is None:
        return None
    end = _parse_app_timestamp(
        _first_nested(
            item,
            "endTime",
            "endedAt",
            "stopTime",
            "stoppedAt",
            "finishTime",
            "completedAt",
        )
    )
    end_inferred = end is None
    if end is None:
        end = start

    transaction_id = _display_text(
        _first_nested(item, "transactionId", "id", "uuid")
    ) or None
    session_id = _display_text(
        _first_nested(item, "sessionId", "chargeSessionId")
    ) or None
    provider = _display_text(
        _first_nested(
            item,
            "serviceProviderName",
            "providerName",
            "operatorName",
            "networkName",
            "provider",
            "operator",
        )
    ) or None
    comment = _display_text(_first_nested(item, "comment", "details", "note"))
    station_name = _display_text(
        _first_nested(
            item,
            "stationName",
            "siteName",
            "locationName",
            "evChargeSiteName",
        )
    ) or None
    if station_name is None and comment and _parse_energy(comment) is None:
        station_name = comment
    station_address = _display_text(
        _first_nested(item, "stationAddress", "siteAddress", "address")
    ) or None
    energy_value, energy_key = _first_nested_with_key(
        item,
        "energyKwh",
        "chargedEnergyKwh",
        "energyUsedKwh",
        "energy",
        "energyUsed",
        "chargedEnergy",
        "consumedEnergy",
    )
    energy = _parse_app_energy(energy_value, energy_key)
    if energy is None:
        energy = _parse_energy(comment) or _parse_energy(service)
    cost_value, cost_key = _first_nested_with_key(
        item,
        "cost",
        "amount",
        "totalCost",
        "price",
    )
    cost = _parse_app_cost(cost_value, cost_key)
    duration = _duration_between(start, end) if not end_inferred else None

    return {
        "transaction_id": transaction_id or session_id,
        "session_id": session_id,
        "source_page": source_page,
        "provider": provider,
        "operator": provider,
        "service": service or service_type or None,
        "service_code": service_code or None,
        "charge_type": _display_text(
            _first_nested(item, "chargeType", "paymentType")
        )
        or None,
        "station_name": station_name,
        "station_address": station_address,
        "connector_code": _display_text(
            _first_nested(item, "connectorCode", "evseId", "connectorId")
        )
        or None,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "end_inferred": end_inferred,
        "duration_minutes": duration,
        "energy_kwh": round(energy, 3) if energy is not None else None,
        "cost_eur": round(cost, 4) if cost is not None else None,
        "transaction_status": _display_text(
            _first_nested(item, "status", "transactionStatus", "state")
        )
        or None,
        "is_commission": False,
    }


def _find_record_list(
    payload: Any,
    names: tuple[str, ...],
    *,
    allow_data_list: bool = False,
) -> list[Mapping[str, Any]]:
    wanted = {_normalize(name) for name in names}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if _normalize(key) in wanted and isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        if allow_data_list and isinstance(payload.get("data"), list):
            return [
                item for item in payload["data"] if isinstance(item, Mapping)
            ]
        for value in payload.values():
            found = _find_record_list(
                value,
                names,
                allow_data_list=allow_data_list,
            )
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_record_list(
                value,
                names,
                allow_data_list=allow_data_list,
            )
            if found:
                return found
    return []


def _first_nested(value: Any, *names: str) -> Any:
    result, _ = _first_nested_with_key(value, *names)
    return result


def _first_nested_with_key(value: Any, *names: str) -> tuple[Any, str | None]:
    wanted = {_normalize(name) for name in names}
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize(key) in wanted and item not in (None, ""):
                return item, str(key)
        for item in value.values():
            if isinstance(item, (Mapping, list)):
                nested, key = _first_nested_with_key(item, *names)
                if nested not in (None, ""):
                    return nested, key
    elif isinstance(value, list):
        for item in value:
            nested, key = _first_nested_with_key(item, *names)
            if nested not in (None, ""):
                return nested, key
    return None, None


def _display_text(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "code", "id"):
            if value.get(key) not in (None, ""):
                return str(value[key]).strip()
        return ""
    return str(value or "").strip()


def _parse_app_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            timestamp = float(text)
        except ValueError:
            timestamp = None
        if timestamp is not None:
            if timestamp > 10_000_000_000:
                timestamp /= 1000.0
            try:
                return datetime.fromtimestamp(timestamp, tz=UTC)
            except (OSError, OverflowError, ValueError):
                return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
            for date_format in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%d.%m.%Y %H:%M:%S",
                "%d.%m.%Y %H:%M",
            ):
                try:
                    parsed = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    continue
            if parsed is None:
                return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=RIGA)
    return parsed.astimezone(UTC)


def _parse_app_energy(value: Any, field_name: str | None) -> float | None:
    number = _number(value)
    if number is None:
        return _parse_energy(_display_text(value))
    normalized_key = _normalize(field_name)
    if "kwh" not in normalized_key and ("wh" in normalized_key or number > 200):
        number /= 1000.0
    return number if number >= 0 else None


def _parse_app_cost(value: Any, field_name: str | None) -> float | None:
    number = _number(value)
    if number is None:
        return None
    normalized_key = _normalize(field_name)
    if normalized_key in {"cost", "amount", "totalcost"}:
        number /= 100.0
    return number


def _number(value: Any) -> float | None:
    if isinstance(value, Mapping):
        value = next(
            (
                value[key]
                for key in ("value", "amount", "total", "number")
                if value.get(key) not in (None, "")
            ),
            None,
        )
    if isinstance(value, (int, float)):
        return float(value)
    return _parse_decimal(_display_text(value))


def _duration_between(start: datetime, end: datetime) -> int:
    return max(0, round((end - start).total_seconds() / 60.0))


def _app_records_match(
    transaction: Mapping[str, Any], session: Mapping[str, Any]
) -> bool:
    transaction_ids = {
        str(transaction.get(key))
        for key in ("transaction_id", "session_id")
        if transaction.get(key)
    }
    session_ids = {
        str(session.get(key))
        for key in ("transaction_id", "session_id")
        if session.get(key)
    }
    if transaction_ids & session_ids:
        return True
    transaction_start = _parse_app_timestamp(transaction.get("start"))
    session_start = _parse_app_timestamp(session.get("start"))
    if transaction_start is None or session_start is None:
        return False
    if abs((transaction_start - session_start).total_seconds()) > 30 * 60:
        return False
    first_provider = _normalize(transaction.get("provider"))
    second_provider = _normalize(session.get("provider"))
    return not first_provider or not second_provider or first_provider == second_provider


def _app_record_distance(
    transaction: Mapping[str, Any], session: Mapping[str, Any]
) -> float:
    first = _parse_app_timestamp(transaction.get("start"))
    second = _parse_app_timestamp(session.get("start"))
    if first is None or second is None:
        return float("inf")
    return abs((first - second).total_seconds())


def _parse_direct_interval(
    date_text: str, time_text: str
) -> tuple[datetime | None, datetime | None]:
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)
    times = re.findall(r"\d{1,2}:\d{2}", time_text)
    if date_match is None or len(times) < 2:
        return None, None
    return _local_interval(date_match.group(0), times[0], times[1])


def _parse_mobile_interval(
    value: str,
) -> tuple[datetime | None, datetime | None]:
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    times = re.findall(r"\d{1,2}:\d{2}", value)
    if date_match is None or len(times) < 2:
        return None, None
    return _local_interval(date_match.group(0), times[0], times[1])


def _local_interval(
    date_text: str, start_text: str, end_text: str
) -> tuple[datetime, datetime]:
    start = datetime.strptime(
        f"{date_text} {start_text}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=RIGA)
    end = datetime.strptime(
        f"{date_text} {end_text}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=RIGA)
    if end < start:
        end += timedelta(days=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def _parse_energy(value: str | None) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*kwh", value or "", re.IGNORECASE)
    return _parse_decimal(match.group(1)) if match else None


def _parse_decimal(value: str | None) -> float | None:
    match = re.search(r"-?\d+(?:[.,]\d+)?", (value or "").replace(" ", ""))
    if match is None:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _is_elektrum_record(record: Mapping[str, Any]) -> bool:
    if is_elektrum_station(record):
        return True
    service = _normalize(record.get("service"))
    return any(marker in service for marker in ELEKTRUM_MARKERS)


def _best_commission_reference(
    commission: Mapping[str, Any], base_records: list[dict[str, Any]]
) -> dict[str, Any] | None:
    start = commission.get("start")
    end = commission.get("end")
    candidates = [
        item
        for item in base_records
        if item.get("source_page") == commission.get("source_page")
        and item.get("start") == start
        and item.get("end") == end
    ]
    if not candidates:
        return None
    service = _normalize(commission.get("service"))
    return max(
        candidates,
        key=lambda item: int(_normalize(item.get("provider")) in service),
    )


def _merge_duplicate(
    current: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    result = dict(current)
    source_pages = set(result.get("source_pages") or [result.get("source_page")])
    source_pages.add(incoming.get("source_page"))
    result["source_pages"] = sorted(item for item in source_pages if item)

    transaction_ids = set(
        result.get("transaction_ids") or [result.get("transaction_id")]
    )
    transaction_ids.add(incoming.get("transaction_id"))
    result["transaction_ids"] = sorted(item for item in transaction_ids if item)

    if result.get("energy_kwh") is None and incoming.get("energy_kwh") is not None:
        result["energy_kwh"] = incoming["energy_kwh"]
        result["amount_text"] = incoming.get("amount_text")
    if result.get("end_inferred") and not incoming.get("end_inferred"):
        result["start"] = incoming.get("start") or result.get("start")
        result["end"] = incoming.get("end") or result.get("end")
        result["duration_minutes"] = incoming.get("duration_minutes")
        result["end_inferred"] = False
    for key in (
        "station_name",
        "station_address",
        "connector_code",
        "transaction_status",
        "charge_type",
        "service_code",
    ):
        if result.get(key) in (None, "") and incoming.get(key) not in (None, ""):
            result[key] = incoming[key]
    if incoming.get("source_page") == "payments_mobile":
        result["cost_eur"] = incoming.get("cost_eur")
        result["vat_eur"] = incoming.get("vat_eur")
    result["commission_cost_eur"] = round(
        (_as_float(result.get("commission_cost_eur")) or 0.0)
        + (_as_float(incoming.get("commission_cost_eur")) or 0.0),
        4,
    )
    return result


def _mobilly_records_match(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> bool:
    if first.get("source_page") == second.get("source_page"):
        return False
    first_start = _parse_app_timestamp(first.get("start"))
    second_start = _parse_app_timestamp(second.get("start"))
    if first_start is None or second_start is None:
        return False
    if abs((first_start - second_start).total_seconds()) > 10 * 60:
        return False
    first_provider = _normalize(first.get("provider"))
    second_provider = _normalize(second.get("provider"))
    if first_provider and second_provider and not (
        first_provider == second_provider
        or first_provider in second_provider
        or second_provider in first_provider
    ):
        return False
    if first.get("end_inferred") or second.get("end_inferred"):
        return True
    first_end = _parse_app_timestamp(first.get("end"))
    second_end = _parse_app_timestamp(second.get("end"))
    return bool(
        first_end
        and second_end
        and abs((first_end - second_end).total_seconds()) <= 20 * 60
    )


def _cached_records_match(
    fresh: Mapping[str, Any], cached: Mapping[str, Any]
) -> bool:
    fresh_account = str(fresh.get("account_id") or "")
    cached_account = str(cached.get("account_id") or "")
    if fresh_account and cached_account and fresh_account != cached_account:
        return False

    fresh_id = str(fresh.get("transaction_id") or "")
    cached_id = str(cached.get("transaction_id") or "")
    if fresh_id and cached_id and fresh_id == cached_id:
        return True

    first_start = _parse_app_timestamp(fresh.get("start"))
    second_start = _parse_app_timestamp(cached.get("start"))
    if first_start is None or second_start is None:
        return False
    if abs((first_start - second_start).total_seconds()) > 10 * 60:
        return False

    first_provider = _normalize(fresh.get("provider"))
    second_provider = _normalize(cached.get("provider"))
    if first_provider and second_provider and not (
        first_provider == second_provider
        or first_provider in second_provider
        or second_provider in first_provider
    ):
        return False

    if fresh.get("end_inferred") or cached.get("end_inferred"):
        return True
    first_end = _parse_app_timestamp(fresh.get("end"))
    second_end = _parse_app_timestamp(cached.get("end"))
    return bool(
        first_end
        and second_end
        and abs((first_end - second_end).total_seconds()) <= 20 * 60
    )


def _backfill_cached_app_fields(
    fresh: dict[str, Any], cached: Mapping[str, Any]
) -> None:
    source_pages = set(fresh.get("source_pages") or [fresh.get("source_page")])
    source_pages.update(cached.get("source_pages") or [cached.get("source_page")])
    fresh["source_pages"] = sorted(item for item in source_pages if item)

    if fresh.get("end_inferred") and not cached.get("end_inferred"):
        fresh["start"] = cached.get("start") or fresh.get("start")
        fresh["end"] = cached.get("end") or fresh.get("end")
        fresh["duration_minutes"] = cached.get("duration_minutes")
        fresh["end_inferred"] = False

    for key in (
        "session_id",
        "station_name",
        "station_address",
        "connector_code",
        "transaction_status",
        "charge_type",
        "service_code",
        "energy_kwh",
    ):
        if fresh.get(key) in (None, "") and cached.get(key) not in (None, ""):
            fresh[key] = cached[key]

    energy = _as_float(fresh.get("energy_kwh"))
    total_cost = _as_float(fresh.get("total_cost_eur"))
    fresh["provider_reported_energy"] = energy is not None and energy > 0
    if total_cost is not None and energy is not None and energy > 0:
        fresh["total_rate_c_per_kwh"] = round(total_cost / energy * 100.0, 3)


def _operator_values(value: Any, field_name: str | None = None) -> list[str]:
    """Collect normalized operator-like values from a nested API record."""
    if isinstance(value, Mapping):
        values: list[str] = []
        for key, item in value.items():
            normalized_key = _normalize(key)
            if normalized_key in _OPERATOR_FIELDS or field_name in _OPERATOR_FIELDS:
                values.extend(_operator_values(item, normalized_key))
            elif isinstance(item, Mapping):
                values.extend(_operator_values(item))
            elif isinstance(item, list):
                values.extend(
                    nested
                    for child in item
                    if isinstance(child, Mapping)
                    for nested in _operator_values(child)
                )
        return values
    if isinstance(value, list):
        return [
            normalized
            for item in value
            for normalized in _operator_values(item, field_name)
        ]
    if field_name in _OPERATOR_FIELDS and value is not None:
        return [_normalize(value)]
    return []


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_header(value: Any) -> str:
    return _normalize(value)


def _normalize(value: Any) -> str:
    """Normalize labels so punctuation and diacritics cannot bypass a match."""
    text = unicodedata.normalize("NFKD", str(value or "")).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
