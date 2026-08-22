"""Validation helpers for persisted Renault driving-cost history."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date
from math import isfinite
from typing import Any

_DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMERIC_FIELDS = ("km", "energy_kwh", "cost_eur")


def normalize_cost_days(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return safe, consistently rounded daily cost records."""
    normalized: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("Cost-history records must be objects")
        day = str(record.get("day") or "").strip()
        if not _DAY_PATTERN.fullmatch(day):
            raise ValueError(f"Invalid cost-history day: {day!r}")
        try:
            date.fromisoformat(day)
        except ValueError as err:
            raise ValueError(f"Invalid cost-history day: {day!r}") from err

        values: dict[str, float] = {}
        for field in _NUMERIC_FIELDS:
            try:
                value = float(record.get(field, 0))
            except (TypeError, ValueError) as err:
                raise ValueError(f"Invalid {field} for {day}") from err
            if not isfinite(value) or value < 0:
                raise ValueError(f"Invalid {field} for {day}")
            values[field] = value

        try:
            trips = int(record.get("trips", 0))
        except (TypeError, ValueError) as err:
            raise ValueError(f"Invalid trips for {day}") from err
        if trips < 0:
            raise ValueError(f"Invalid trips for {day}")

        normalized[day] = {
            "day": day,
            "km": round(values["km"], 3),
            "energy_kwh": round(values["energy_kwh"], 3),
            "cost_eur": round(values["cost_eur"], 4),
            "trips": trips,
        }

    return [normalized[day] for day in sorted(normalized)]
