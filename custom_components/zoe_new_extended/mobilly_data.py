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
        current = merged.get(key)
        if current is None:
            merged[key] = dict(record)
            continue
        merged[key] = _merge_duplicate(current, record)

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
    if incoming.get("source_page") == "payments_mobile":
        result["cost_eur"] = incoming.get("cost_eur")
        result["vat_eur"] = incoming.get("vat_eur")
    result["commission_cost_eur"] = round(
        (_as_float(result.get("commission_cost_eur")) or 0.0)
        + (_as_float(incoming.get("commission_cost_eur")) or 0.0),
        4,
    )
    return result


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
