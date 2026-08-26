"""Validation helpers for retained Renault GPS route history."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any


def normalize_route_points(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return safe, ordered GPS points, replacing duplicate timestamps."""
    normalized: dict[int, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("Route-history points must be objects")
        try:
            timestamp = int(record.get("t"))
            latitude = float(record.get("lat"))
            longitude = float(record.get("lon"))
        except (TypeError, ValueError) as err:
            raise ValueError("Invalid route-history point") from err

        if timestamp < 0 or not isfinite(latitude) or not isfinite(longitude):
            raise ValueError("Invalid route-history point")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Invalid route-history coordinates")

        point: dict[str, Any] = {
            "t": timestamp,
            "lat": round(latitude, 7),
            "lon": round(longitude, 7),
        }
        raw_accuracy = record.get("accuracy")
        if raw_accuracy is not None:
            try:
                accuracy = float(raw_accuracy)
            except (TypeError, ValueError) as err:
                raise ValueError("Invalid route-history accuracy") from err
            if not isfinite(accuracy) or accuracy < 0:
                raise ValueError("Invalid route-history accuracy")
            point["accuracy"] = round(accuracy, 1)

        normalized[timestamp] = point

    return [normalized[timestamp] for timestamp in sorted(normalized)]
