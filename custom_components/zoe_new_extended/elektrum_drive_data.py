"""Pure helpers for Elektrum Drive station and tariff data."""

from __future__ import annotations

import html
from html.parser import HTMLParser
import json
import math
from typing import Any


ACTIVE_CONNECTOR_STATUSES = frozenset(
    {
        "charging",
        "finishing",
        "occupied",
        "preparing",
        "suspendedev",
        "suspendedevse",
    }
)


class _LivewireSnapshotParser(HTMLParser):
    """Collect Livewire snapshots without depending on an HTML library."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.snapshots: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Record every wire:snapshot attribute."""
        for name, value in attrs:
            if name == "wire:snapshot" and value:
                self.snapshots.append(value)


def _unwrap_livewire(value: Any) -> Any:
    """Remove Livewire synthesizer metadata from a serialized value."""
    if isinstance(value, list):
        if (
            len(value) == 2
            and isinstance(value[1], dict)
            and "s" in value[1]
        ):
            return _unwrap_livewire(value[0])
        return [_unwrap_livewire(item) for item in value]
    if isinstance(value, dict):
        return {key: _unwrap_livewire(item) for key, item in value.items()}
    return value


def _mapping(value: Any) -> dict[str, Any]:
    """Return the first mapping represented by a Livewire field."""
    value = _unwrap_livewire(value)
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return {}


def parse_connector_page(page: str) -> dict[str, Any]:
    """Extract connector status and the current public tariff from Direct."""
    parser = _LivewireSnapshotParser()
    parser.feed(page)
    for raw_snapshot in parser.snapshots:
        try:
            snapshot = json.loads(html.unescape(raw_snapshot))
        except (TypeError, ValueError):
            continue
        connector = _mapping(snapshot.get("data", {}).get("connector"))
        if not connector.get("code"):
            continue
        tariff = _mapping(connector.get("chargingTariff"))
        connector_type = _mapping(connector.get("connectorType"))
        charging_power = _mapping(connector.get("chargingPowerType"))
        transformed_price = _mapping(tariff.get("priceTransformed"))
        return {
            "connector_id": connector.get("id"),
            "code": connector.get("code"),
            "station_address": connector.get("stationAddress"),
            "status": connector.get("status"),
            "connector_type": connector_type.get("name"),
            "power_kw": _as_float(charging_power.get("kilowatts")),
            "tariff_id": tariff.get("id"),
            "price_c_per_kwh": _as_float(tariff.get("price")),
            "price_formatted": transformed_price.get("formatted"),
            "price_unit": tariff.get("unit"),
        }
    raise ValueError("Elektrum Direct connector snapshot was not found")


def station_connectors(station: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the public station API connector list."""
    connectors = []
    for point in station.get("chargingPoints", []):
        for connector in point.get("connectors", []):
            code = connector.get("code")
            if not code:
                continue
            connectors.append(
                {
                    "code": code,
                    "connector_type": connector.get("type"),
                    "current_type": connector.get("currentType"),
                    "power_kw": _power_kw(connector.get("chargingPowerType")),
                }
            )
    return connectors


def station_coordinates(station: dict[str, Any]) -> tuple[float, float] | None:
    """Parse the public API's semicolon-separated station coordinates."""
    coordinates = str(station.get("coordinates") or "").split(";")
    if len(coordinates) != 2:
        return None
    latitude = _as_float(coordinates[0])
    longitude = _as_float(coordinates[1])
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def haversine_distance_m(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return the great-circle distance between two WGS84 coordinates."""
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)
    latitude_a_rad = math.radians(latitude_a)
    latitude_b_rad = math.radians(latitude_b)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a_rad)
        * math.cos(latitude_b_rad)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 6371000 * 2 * math.asin(math.sqrt(value))


def nearest_station(
    stations: list[dict[str, Any]],
    latitude: float,
    longitude: float,
) -> tuple[dict[str, Any] | None, float | None]:
    """Find the closest station with valid coordinates."""
    closest = None
    closest_distance = None
    for station in stations:
        coordinates = station_coordinates(station)
        if coordinates is None:
            continue
        distance = haversine_distance_m(
            latitude,
            longitude,
            coordinates[0],
            coordinates[1],
        )
        if closest_distance is None or distance < closest_distance:
            closest = station
            closest_distance = distance
    return closest, closest_distance


def select_connector(
    connectors: list[dict[str, Any]],
    *,
    is_charging: bool,
    observed_power_kw: float | None,
) -> dict[str, Any] | None:
    """Select the connector most likely used by the vehicle."""
    if not connectors:
        return None

    def score(connector: dict[str, Any]) -> tuple[float, float, float]:
        status = str(connector.get("status") or "").lower()
        power = _as_float(connector.get("power_kw")) or 0.0
        active_score = 100.0 if is_charging and status in ACTIVE_CONNECTOR_STATUSES else 0
        availability_score = 5.0 if not is_charging and status == "available" else 0
        compatibility_score = 0.0
        power_distance = 1000.0
        if observed_power_kw is not None and observed_power_kw > 0:
            current_type = str(connector.get("current_type") or "").upper()
            if observed_power_kw <= 22 and current_type == "AC":
                compatibility_score += 4.0
            if observed_power_kw > 22 and current_type == "DC":
                compatibility_score += 4.0
            if power >= observed_power_kw * 0.8:
                compatibility_score += 2.0
            power_distance = abs(power - observed_power_kw)
        return (
            active_score + availability_score + compatibility_score,
            -power_distance,
            -power,
        )

    return max(connectors, key=score)


def price_after_discount(
    price_c_per_kwh: float | None,
    *,
    partner: bool,
    discount_percent: float,
) -> float | None:
    """Apply the Elektrum postpaid discount only on its own network."""
    if price_c_per_kwh is None:
        return None
    discount = 0.0 if partner else min(100.0, max(0.0, discount_percent))
    return round(price_c_per_kwh * (1 - discount / 100), 4)


def _power_kw(value: Any) -> float | None:
    """Parse values such as ``22kW`` from the public station API."""
    if isinstance(value, str):
        value = value.lower().replace("kw", "").strip()
    return _as_float(value)


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
