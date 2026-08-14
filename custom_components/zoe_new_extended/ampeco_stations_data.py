"""Normalize public AMPECO charging-location responses."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from typing import Any


OCCUPIED_STATUSES = frozenset(
    {
        "charging",
        "finishing",
        "occupied",
        "preparing",
        "reserved",
        "suspendedev",
        "suspendedevse",
    }
)


def normalize_ampeco_catalog(
    locations: list[dict[str, Any]],
    tariffs: list[dict[str, Any]],
    *,
    provider: str,
    provider_group: str,
    operator: str,
) -> list[dict[str, Any]]:
    """Normalize one AMPECO location batch and its tariff table."""
    tariffs_by_id = {
        str(tariff.get("id")): tariff
        for tariff in tariffs
        if isinstance(tariff, Mapping) and tariff.get("id") is not None
    }
    return [
        normalized
        for location in locations
        if isinstance(location, dict)
        if (
            normalized := normalize_ampeco_station(
                location,
                tariffs_by_id,
                provider=provider,
                provider_group=provider_group,
                operator=operator,
            )
        )
        is not None
    ]


def normalize_ampeco_station(
    location: dict[str, Any],
    tariffs_by_id: Mapping[str, Mapping[str, Any]],
    *,
    provider: str,
    provider_group: str,
    operator: str,
) -> dict[str, Any] | None:
    """Normalize one location returned by AMPECO's public app API."""
    station_id = location.get("id")
    coordinates = _coordinates(location.get("location"))
    if station_id is None or coordinates is None:
        return None

    station_updated = location.get("updatedAt")
    connectors: list[dict[str, Any]] = []
    connector_index = 0
    for zone in _mapping_list(location.get("zones")):
        for evse in _mapping_list(zone.get("evses")):
            raw_connectors = _mapping_list(evse.get("connectors")) or [{}]
            for raw_connector in raw_connectors:
                connector_index += 1
                tariff = tariffs_by_id.get(str(evse.get("tariffId")), {})
                status = _status(evse)
                connector = {
                    "code": _connector_code(provider, evse),
                    "provider_connector_id": str(
                        raw_connector.get("id") or evse.get("id") or ""
                    ),
                    "identifier": evse.get("identifier"),
                    "emi3_identifier": evse.get("emi3Identifier"),
                    "roaming_evse_id": evse.get("roamingEvseId"),
                    "connector_type": (
                        raw_connector.get("name")
                        or raw_connector.get("icon")
                        or "Unknown"
                    ),
                    "format": raw_connector.get("format"),
                    "current_type": evse.get("currentType"),
                    "power_kw": _power_kw(evse.get("maxPower")),
                    "connector_index": connector_index,
                    "connector_number": _positive_int(evse.get("networkId"))
                    or connector_index,
                    "status": status,
                    "status_observed_since": station_updated,
                    "status_source": f"{provider}_public_api",
                }
                connector.update(_tariff_values(tariff))
                connectors.append(connector)

    statuses = [str(item.get("status") or "unknown") for item in connectors]
    available = statuses.count("available")
    occupied = sum(status in OCCUPIED_STATUSES for status in statuses)
    price = _lowest_price(connectors)
    name = str(location.get("name") or f"{operator} {station_id}").strip()
    address = _clean_text(location.get("address"))
    descriptions = _descriptions(location, exclude=(name, address))
    result: dict[str, Any] = {
        "provider": provider,
        "provider_group": provider_group,
        "id": str(station_id),
        "name": name,
        "description": descriptions[0] if descriptions else None,
        "descriptions": descriptions,
        "address": address,
        "city": None,
        "country": _country_from_timezone(location.get("timezone")),
        "latitude": coordinates[0],
        "longitude": coordinates[1],
        "partner": False,
        "operator": operator,
        "connectors": connectors,
        "connector_count": len(connectors),
        "max_power_kw": max(
            (
                float(item["power_kw"])
                for item in connectors
                if item.get("power_kw") is not None
            ),
            default=None,
        ),
        "availability": (
            "available"
            if available
            else "occupied"
            if occupied
            else "unavailable"
            if connectors and any(status != "unknown" for status in statuses)
            else "unknown"
        ),
        "available_connectors": available,
        "occupied_connectors": occupied,
        "live_data_available": True,
        "connector_live_data_available": True,
        "status_source": f"{provider}_public_api",
        "detail_source": f"{provider}_public_api",
        "updated_at": station_updated,
    }
    if price:
        result.update(price)
        result["price_source"] = f"{provider}_public_api"
    return result


def _connector_code(provider: str, evse: Mapping[str, Any]) -> str:
    for key in ("emi3Identifier", "roamingEvseId"):
        value = str(evse.get(key) or "").strip().upper().replace(" ", "")
        if value:
            return value
    return f"{provider}:evse:{evse.get('id') or evse.get('identifier') or 'unknown'}"


def _tariff_values(tariff: Mapping[str, Any]) -> dict[str, Any]:
    if not tariff:
        return {}
    energy_eur = _as_float(tariff.get("priceForEnergy"))
    duration_eur = _as_float(tariff.get("priceForDuration"))
    connection_eur = _as_float(tariff.get("connectionFee"))
    session_eur = _as_float(tariff.get("priceForSession"))
    minimum_eur = _as_float(tariff.get("minPrice"))

    if energy_eur is not None:
        price_value = round(energy_eur * 100, 4)
        price_unit = "kWh"
        formatted = f"{price_value:g} c/kWh"
    elif duration_eur is not None:
        price_value = round(duration_eur * 100, 4)
        price_unit = "min"
        formatted = f"{price_value:g} c/min"
    else:
        price_value = None
        price_unit = None
        formatted = None

    extras = []
    if connection_eur:
        extras.append(f"EUR {connection_eur:.2f}/connection")
    if session_eur:
        extras.append(f"EUR {session_eur:.2f}/session")
    if formatted and extras:
        formatted = f"{formatted} + {' + '.join(extras)}"
    elif extras:
        formatted = " + ".join(extras)

    return {
        "tariff_id": str(tariff.get("id") or ""),
        "price_c_per_kwh": (
            round(energy_eur * 100, 4) if energy_eur is not None else None
        ),
        "price_value": price_value,
        "price_unit": price_unit,
        "price_formatted": formatted,
        "price_source": "operator_public_tariff",
        "currency": tariff.get("currencyCode") or "EUR",
        "connection_fee_eur": connection_eur,
        "session_fee_eur": session_eur,
        "minimum_price_eur": minimum_eur,
        "prices_include_tax": tariff.get("arePricesTaxInclusive"),
    }


def _lowest_price(connectors: list[dict[str, Any]]) -> dict[str, Any]:
    priced = [
        item
        for item in connectors
        if item.get("price_value") is not None and item.get("price_unit")
    ]
    if not priced:
        return {}
    energy = [item for item in priced if item.get("price_unit") == "kWh"]
    best = min(energy or priced, key=lambda item: float(item["price_value"]))
    return {
        key: best.get(key)
        for key in (
            "price_c_per_kwh",
            "price_value",
            "price_unit",
            "price_formatted",
        )
    }


def _status(evse: Mapping[str, Any]) -> str:
    value = re.sub(r"[^a-z]", "", str(evse.get("status") or "").casefold())
    if evse.get("isAvailable") is True or value == "available":
        return "available"
    if value in OCCUPIED_STATUSES:
        return value
    if value in {
        "blocked",
        "faulted",
        "inoperative",
        "offline",
        "outoforder",
        "unavailable",
    } or evse.get("isLongTermUnavailable") is True:
        return "unavailable"
    return value or "unknown"


def _coordinates(value: Any) -> tuple[float, float] | None:
    parts = str(value or "").split(",")
    if len(parts) != 2:
        return None
    latitude = _as_float(parts[0])
    longitude = _as_float(parts[1])
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def _power_kw(value: Any) -> float | None:
    number = _as_float(value)
    if number is None:
        return None
    return number / 1000.0 if number > 1000 else number


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _descriptions(
    location: Mapping[str, Any],
    *,
    exclude: tuple[Any, ...],
) -> list[str]:
    excluded = {_clean_text(item).casefold() for item in exclude if item}
    result = []
    seen = set()
    for key in (
        "description",
        "detailed_description",
        "additional_description",
        "what3words_address",
    ):
        text = _clean_text(location.get(key))
        normalized = text.casefold()
        if not text or normalized in excluded or normalized in seen:
            continue
        seen.add(normalized)
        result.append(text)
    return result


def _clean_text(value: Any) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def _country_from_timezone(value: Any) -> str | None:
    city = str(value or "").rsplit("/", 1)[-1].casefold()
    return {
        "riga": "Latvia",
        "tallinn": "Estonia",
        "vilnius": "Lithuania",
    }.get(city)


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None
