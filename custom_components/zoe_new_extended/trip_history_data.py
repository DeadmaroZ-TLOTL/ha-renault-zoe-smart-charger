"""Validation helpers for persisted Renault trip and surface history."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from math import isfinite
import re
from typing import Any


_DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_DISTANCE_FIELDS = ("km", "hard", "loose", "unknown")
_SPEED_FIELDS = ("average_speed", "max_speed")


def _number(record: Mapping[str, Any], field: str) -> float:
    try:
        value = float(record.get(field, 0))
    except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid {field}") from err
    if not isfinite(value) or value < 0:
        raise ValueError(f"Invalid {field}")
    return value


def normalize_trip_records(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return safe, ordered trip records, replacing duplicate record IDs."""
    normalized: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("Trip-history records must be objects")

        record_id = str(record.get("id") or "").strip()
        if not _ID_PATTERN.fullmatch(record_id):
            raise ValueError("Invalid trip-history ID")

        day = str(record.get("day") or "").strip()
        if not _DAY_PATTERN.fullmatch(day):
            raise ValueError(f"Invalid trip-history day: {day!r}")
        try:
            date.fromisoformat(day)
        except ValueError as err:
            raise ValueError(f"Invalid trip-history day: {day!r}") from err

        try:
            start = int(record.get("start"))
            end = int(record.get("end"))
        except (TypeError, ValueError) as err:
            raise ValueError("Invalid trip-history timestamps") from err
        if start < 0 or end <= start:
            raise ValueError("Invalid trip-history timestamps")

        values = {field: _number(record, field) for field in _DISTANCE_FIELDS}
        if values["km"] <= 0:
            raise ValueError("Invalid km")
        surface_total = values["hard"] + values["loose"] + values["unknown"]
        if surface_total <= 0:
            values["unknown"] = values["km"]
        elif abs(surface_total - values["km"]) > 0.001:
            scale = values["km"] / surface_total
            for field in ("hard", "loose", "unknown"):
                values[field] *= scale

        normalized_record: dict[str, Any] = {
            "id": record_id,
            "day": day,
            "start": start,
            "end": end,
            "km": round(values["km"], 3),
            "hard": round(values["hard"], 3),
            "loose": round(values["loose"], 3),
            "unknown": round(values["unknown"], 3),
            "coverage": round(
                min(100.0, (values["hard"] + values["loose"]) / values["km"] * 100),
                2,
            ),
            "source": "renault_gps_osm",
        }
        for field in _SPEED_FIELDS:
            raw_value = record.get(field)
            if raw_value is None:
                normalized_record[field] = None
                continue
            value = _number(record, field)
            if value > 400:
                raise ValueError(f"Invalid {field}")
            normalized_record[field] = round(value, 2)

        normalized[record_id] = normalized_record

    return sorted(normalized.values(), key=lambda record: (record["start"], record["id"]))
