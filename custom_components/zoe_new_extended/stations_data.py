"""Pure helpers for normalizing public charging-station catalog data."""

from __future__ import annotations

import html
import math
import re
from collections.abc import Mapping
from typing import Any

from .elektrum_drive_data import (
    haversine_distance_m,
    station_connectors,
    station_coordinates,
)


EMOBI_PRICE_C_PER_MIN = 19.0
OCCUPIED_STATUSES = frozenset(
    {
        "charging",
        "finishing",
        "occupied",
        "preparing",
        "suspendedev",
        "suspendedevse",
    }
)
DESCRIPTION_KEYS = (
    "description",
    "instructions",
    "instruction",
    "accessInstructions",
    "accessInstruction",
    "access_instructions",
    "accessComments",
    "access_comments",
    "accessInfo",
    "access_info",
    "additionalInformation",
    "additional_information",
    "additionalInfo",
    "additional_info",
    "directions",
    "locationDescription",
    "location_description",
    "remarks",
    "remark",
    "comments",
    "comment",
    "notes",
    "note",
    "openingHours",
    "opening_hours",
    "hours",
)


def normalize_elektrum_station(
    station: dict[str, Any],
    *,
    language: str = "lv",
) -> dict[str, Any] | None:
    """Normalize one Elektrum Drive public catalog record."""
    coordinates = station_coordinates(station)
    station_id = station.get("id")
    if station_id is None or coordinates is None:
        return None

    translation = next(
        (
            item
            for item in station.get("translatable", [])
            if isinstance(item, dict) and item.get("locale") == language
        ),
        {},
    )
    connectors = station_connectors(station)
    fallback_name = next(
        (
            point.get("name")
            for point in station.get("chargingPoints", [])
            if isinstance(point, dict) and point.get("name")
        ),
        None,
    )
    operator = _elektrum_operator(station, translation)
    name = translation.get("name") or fallback_name or station.get("address")
    description = _station_description(
        translation,
        station,
        *(point for point in station.get("chargingPoints", []) if isinstance(point, Mapping)),
        language=language,
        exclude=(name, station.get("address"), station.get("city")),
    )
    fallback_price = _operator_fallback_price(operator)
    if fallback_price:
        for connector in connectors:
            connector.update(fallback_price)
            connector["price_source"] = "operator_public_tariff"
    return {
        "provider": "elektrum",
        "provider_group": "elektrum",
        "id": str(station_id),
        "name": name,
        "description": description,
        "descriptions": _merge_descriptions(description),
        "address": station.get("address"),
        "city": station.get("city"),
        "country": station.get("country"),
        "latitude": coordinates[0],
        "longitude": coordinates[1],
        "partner": bool(station.get("partner")),
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
        "availability": "unknown",
        "available_connectors": None,
        "occupied_connectors": None,
        "price_c_per_kwh": (
            fallback_price.get("price_c_per_kwh") if fallback_price else None
        ),
        "price_value": fallback_price.get("price_value") if fallback_price else None,
        "price_unit": fallback_price.get("price_unit") if fallback_price else None,
        "price_formatted": (
            fallback_price.get("price_formatted") if fallback_price else None
        ),
        "price_source": "operator_public_tariff" if fallback_price else None,
        "live_data_available": False,
    }


def normalize_mobilly_station(site: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one Mobilly public catalog record."""
    if site.get("type") != "ev_charge":
        return None
    location = site.get("location")
    coordinates = location.get("coordinates") if isinstance(location, dict) else None
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    longitude = _as_float(coordinates[0])
    latitude = _as_float(coordinates[1])
    site_id = site.get("id")
    if site_id is None or latitude is None or longitude is None:
        return None

    details = site.get("siteDetails")
    raw_connectors = details.get("connectors", []) if isinstance(details, dict) else []
    connectors = []
    connector_count = 0
    for raw in raw_connectors:
        if not isinstance(raw, dict):
            continue
        count = max(1, int(_as_float(raw.get("count")) or 1))
        connector_count += count
        for connector_index in range(1, count + 1):
            connectors.append(
                {
                    "code": f"{site_id}-{raw.get('type') or 'plug'}-{connector_index}",
                    "connector_type": raw.get("type"),
                    "power_kw": _watts_to_kw(raw.get("maxPower")),
                    "count": 1,
                    "connector_index": connector_index,
                    "connector_number": connector_count - count + connector_index,
                    "status": "unknown",
                    "status_observed_since": None,
                    "price_c_per_kwh": None,
                }
            )

    operator = _mobilly_operator(site)
    name = site.get("name") or site.get("description") or f"Mobilly {site_id}"
    address = site.get("description")
    description = _station_description(
        details if isinstance(details, Mapping) else None,
        site,
        language="lv",
        exclude=(name, address),
    )
    fallback_price = _operator_fallback_price(operator)
    if fallback_price:
        for connector in connectors:
            connector.update(fallback_price)
            connector["price_source"] = "operator_public_tariff"

    return {
        "provider": "mobilly",
        "provider_group": "mobilly",
        "id": str(site_id),
        "uid": site.get("uid"),
        "name": name,
        "description": description,
        "descriptions": _merge_descriptions(description),
        "address": address,
        "city": None,
        "country": None,
        "latitude": latitude,
        "longitude": longitude,
        "partner": True,
        "operator": operator,
        "connectors": connectors,
        "connector_count": connector_count,
        "max_power_kw": max(
            (
                float(item["power_kw"])
                for item in connectors
                if item.get("power_kw") is not None
            ),
            default=None,
        ),
        "availability": "unknown",
        "available_connectors": None,
        "occupied_connectors": None,
        "price_c_per_kwh": (
            fallback_price.get("price_c_per_kwh") if fallback_price else None
        ),
        "price_value": fallback_price.get("price_value") if fallback_price else None,
        "price_unit": fallback_price.get("price_unit") if fallback_price else None,
        "price_formatted": (
            fallback_price.get("price_formatted") if fallback_price else None
        ),
        "price_source": "operator_public_tariff" if fallback_price else None,
        "live_data_available": False,
        "live_data_requires_mobile_session": True,
    }


def normalize_emobi_station(feature: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one official e-mobi map feature with live connector data."""
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        return None
    company = str(properties.get("companyName") or "").casefold()
    if company not in {"csdd", "echarge"}:
        return None
    is_csdd = company == "csdd"

    geometry = feature.get("geometry")
    coordinates = geometry.get("coordinates") if isinstance(geometry, Mapping) else None
    longitude = _as_float(coordinates[0]) if isinstance(coordinates, list) else None
    latitude = _as_float(coordinates[1]) if isinstance(coordinates, list) else None
    station_id = properties.get("id")
    if station_id is None or latitude is None or longitude is None:
        return None

    connectors: list[dict[str, Any]] = []
    raw_connectors = properties.get("connectors")
    if not isinstance(raw_connectors, list):
        raw_connectors = []
    for index, raw in enumerate(raw_connectors, start=1):
        if not isinstance(raw, Mapping):
            continue
        connector_number = _as_int(raw.get("rawName")) or index
        connector = {
            "code": str(raw.get("code") or raw.get("id") or ""),
            "connector_type": raw.get("type") or raw.get("name"),
            "power_kw": _as_float(raw.get("maxPowerKw")),
            "current_type": raw.get("currentType"),
            "connector_index": index,
            "connector_number": connector_number,
            "status": _normalize_live_status(raw.get("status")),
            "status_observed_since": None,
            "service_id": raw.get("serviceId"),
        }
        price = _extract_price(raw.get("rate"))
        if price:
            connector.update(price)
            connector["price_source"] = "emobi_public_api"
        connectors.append(connector)

    statuses = [str(item.get("status") or "unknown") for item in connectors]
    available = statuses.count("available")
    occupied = sum(status in OCCUPIED_STATUSES for status in statuses)
    price = _lowest_connector_price(connectors)
    address_data = properties.get("address")
    address_data = address_data if isinstance(address_data, Mapping) else {}
    station_status = _normalize_live_status(properties.get("status"))
    name = properties.get("name") or f"e-mobi {station_id}"
    description = _station_description(
        properties,
        address_data,
        language="lv",
        exclude=(name, address_data.get("street"), address_data.get("city")),
    )
    result = {
        "provider": "emobi" if is_csdd else "emobi_elektrum",
        "provider_group": "emobi" if is_csdd else "elektrum",
        "id": str(station_id),
        "uid": properties.get("uuid"),
        "name": name,
        "description": description,
        "descriptions": _merge_descriptions(description),
        "address": address_data.get("street"),
        "city": address_data.get("city"),
        "country": "Latvia",
        "latitude": latitude,
        "longitude": longitude,
        "partner": True,
        "operator": "e-mobi" if is_csdd else "Elektrum Drive",
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
        "availability": station_status,
        "available_connectors": available,
        "occupied_connectors": occupied,
        "live_data_available": True,
        "connector_live_data_available": True,
        "status_source": "emobi_public_api",
        "detail_source": "emobi_public_api",
    }
    if price:
        result.update(price)
        result["price_source"] = "emobi_public_api"
    return result


def _elektrum_operator(
    station: dict[str, Any], translation: dict[str, Any]
) -> str:
    if not bool(station.get("partner")):
        return "Elektrum Drive"
    name = str(translation.get("name") or "").casefold()
    codes = [
        str(connector.get("code") or "").upper()
        for point in station.get("chargingPoints", [])
        if isinstance(point, dict)
        for connector in point.get("connectors", [])
        if isinstance(connector, dict)
    ]
    if "e-mobi" in name or any(code.startswith("LV*CSD*") for code in codes):
        return "e-mobi"
    return "Elektrum partner network"


def _mobilly_operator(site: dict[str, Any]) -> str:
    searchable = " ".join(
        str(value or "") for value in (site.get("description"), site.get("name"))
    ).casefold()
    if "e-mobi" in searchable or "emobi" in searchable or "csdd" in searchable:
        return "e-mobi"
    for value in (site.get("description"), site.get("name")):
        match = re.match(r"^\s*\(([^)]+)\)", str(value or ""))
        if match:
            return match.group(1).strip()
    return "Mobilly"


def merge_mobilly_statuses(
    stations: list[dict[str, Any]],
    payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Merge Mobilly's compact live site-status response into the catalog."""
    raw_statuses = payload.get("statuses", [])
    if isinstance(payload.get("data"), Mapping):
        raw_statuses = payload["data"].get("statuses", raw_statuses)
    if not isinstance(raw_statuses, list):
        return [dict(station) for station in stations]
    by_id = {
        str(item.get("id")): item
        for item in raw_statuses
        if isinstance(item, Mapping) and item.get("id") is not None
    }
    result = []
    for source in stations:
        station = dict(source)
        status = by_id.get(str(station.get("id")))
        if status is None:
            result.append(station)
            continue
        counts = status.get("connectors")
        counts = counts if isinstance(counts, Mapping) else {}
        available = _as_int(counts.get("available"))
        occupied = _as_int(counts.get("occupied"))
        active = status.get("isActive")
        station.update(
            {
                "availability": (
                    "unavailable"
                    if active is False
                    else "available"
                    if available and available > 0
                    else "occupied"
                    if occupied and occupied > 0
                    else "unknown"
                ),
                "available_connectors": available,
                "occupied_connectors": occupied,
                "live_data_available": True,
                "live_data_requires_mobile_session": False,
                "status_source": "mobilly_app",
            }
        )
        result.append(station)
    return result


def merge_mobilly_station_detail(
    station: dict[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge a protected Mobilly station detail response into one station."""
    detail = _unwrap_detail(payload)
    raw_connectors = _find_connector_records(detail)
    base_connectors = [dict(item) for item in station.get("connectors", [])]
    connectors: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_connectors):
        base = _match_connector(base_connectors, raw, index)
        merged = dict(base or {})
        code = _first_value(raw, "code", "evseId", "evse_id", "connectorId", "id")
        connector_type = _first_value(
            raw, "connectorType", "connector_type", "plugType", "type", "standard"
        )
        status = _first_value(raw, "status", "state", "availability")
        power = _first_value(
            raw, "maxPower", "max_power", "powerKw", "power_kw", "power"
        )
        if code is not None:
            merged["code"] = str(code)
        if connector_type is not None:
            merged["connector_type"] = _display_value(connector_type)
        if status is not None:
            merged["status"] = str(_display_value(status)).lower()
        if power is not None:
            merged["power_kw"] = _watts_to_kw(_display_value(power))
        observed_since = _first_value(
            raw,
            "statusObservedSince",
            "statusSince",
            "occupiedSince",
            "updatedAt",
        )
        if observed_since is not None:
            merged["status_observed_since"] = str(observed_since)
        price = _extract_price(raw)
        if price:
            merged.update(price)
            merged["price_source"] = "mobilly_app"
        connectors.append(merged)

    if not connectors:
        connectors = base_connectors
    statuses = [str(item.get("status") or "unknown").lower() for item in connectors]
    available = statuses.count("available")
    occupied = sum(status in OCCUPIED_STATUSES for status in statuses)
    price = _lowest_connector_price(connectors)
    result = {
        **station,
        "connectors": connectors,
        "connector_count": len(connectors),
        "availability": (
            "available"
            if available
            else "occupied"
            if occupied
            else "unavailable"
            if any(status not in {"", "unknown"} for status in statuses)
            else station.get("availability", "unknown")
        ),
        "available_connectors": available,
        "occupied_connectors": occupied,
        "live_data_available": True,
        "live_data_requires_mobile_session": False,
        "detail_source": "mobilly_app",
    }
    detail_description = _station_description(
        detail,
        language="lv",
        exclude=(station.get("name"), station.get("address"), station.get("city")),
    )
    result["descriptions"] = _merge_descriptions(
        station.get("descriptions"), station.get("description"), detail_description
    )
    if detail_description:
        result["description"] = detail_description
    detail_price = _extract_price(detail)
    if detail_price:
        price = detail_price
    if price:
        result.update(price)
        result["price_source"] = "mobilly_app"
    return result


def deduplicate_stations(
    stations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse the same physical station returned by multiple providers."""
    result: list[dict[str, Any]] = []
    connector_index: dict[str, set[int]] = {}
    spatial_index: dict[tuple[int, int], set[int]] = {}

    def register(index: int, station: Mapping[str, Any]) -> None:
        for code in _station_connector_codes(station):
            connector_index.setdefault(code, set()).add(index)
        cell = _station_spatial_cell(station)
        if cell is not None:
            spatial_index.setdefault(cell, set()).add(index)

    for source in stations:
        station = dict(source)
        candidates: set[int] = set()
        for code in _station_connector_codes(station):
            candidates.update(connector_index.get(code, ()))
        cell = _station_spatial_cell(station)
        if cell is not None:
            for latitude_offset in range(-1, 2):
                for longitude_offset in range(-2, 3):
                    candidates.update(
                        spatial_index.get(
                            (cell[0] + latitude_offset, cell[1] + longitude_offset),
                            (),
                        )
                    )
        duplicate_index = next(
            (
                index
                for index in sorted(candidates)
                if _same_physical_station(result[index], station)
            ),
            None,
        )
        if duplicate_index is None:
            station["source_providers"] = [station.get("provider")]
            station["descriptions"] = _merge_descriptions(
                station.get("descriptions"), station.get("description")
            )
            station["provider_offers"] = _merge_provider_offers(
                station.get("provider_offers"), [_provider_offer(station)]
            )
            station["provider_groups"] = [
                offer["provider_group"] for offer in station["provider_offers"]
            ]
            result.append(station)
            register(len(result) - 1, station)
            continue
        existing = result[duplicate_index]
        primary, secondary = (
            (station, existing)
            if _station_quality(station) > _station_quality(existing)
            else (existing, station)
        )
        merged = dict(primary)
        for key, value in secondary.items():
            if merged.get(key) in (None, "", [], {}) and value not in (
                None,
                "",
                [],
                {},
            ):
                merged[key] = value
        merged["source_providers"] = sorted(
            {
                str(provider)
                for provider in (
                    *existing.get("source_providers", [existing.get("provider")]),
                    station.get("provider"),
                )
                if provider
            }
        )
        merged["provider_offers"] = _merge_provider_offers(
            existing.get("provider_offers"),
            station.get("provider_offers"),
            [_provider_offer(station)],
        )
        merged["descriptions"] = _merge_descriptions(
            existing.get("descriptions"),
            existing.get("description"),
            station.get("descriptions"),
            station.get("description"),
        )
        if not merged.get("description") and merged["descriptions"]:
            merged["description"] = merged["descriptions"][0]
        merged["provider_groups"] = [
            offer["provider_group"] for offer in merged["provider_offers"]
        ]
        merged["name"] = _best_station_name(existing, station)
        result[duplicate_index] = merged
        register(duplicate_index, station)
    return result


def _best_station_name(*stations: Mapping[str, Any]) -> str:
    """Prefer a human-readable site name over an EVSE or catalog identifier."""
    names: list[str] = []
    addresses: list[str] = []
    for station in stations:
        name = str(station.get("name") or "").strip()
        address = str(station.get("address") or "").strip()
        if name:
            names.append(name)
        if address:
            addresses.append(address)
    if names:
        best_name = max(names, key=lambda value: _station_name_quality(value, False))
        if _station_name_quality(best_name, False)[0] > 0:
            return best_name
    if addresses:
        return max(
            addresses,
            key=lambda value: _station_name_quality(value, True),
        )
    return names[0] if names else "Charging station"


def _station_name_quality(value: str, is_address: bool) -> tuple[int, int, int]:
    text = re.sub(r"\s+", " ", value).strip()
    identifier = bool(
        re.fullmatch(r"[A-Z0-9*_.-]{8,}", text.upper())
        and not re.search(r"\s", text)
    )
    has_words = bool(re.search(r"[A-Za-z\u00c0-\u024f]{3,}\s+[A-Za-z\u00c0-\u024f0-9]", text))
    human_score = 0 if identifier else 2 if has_words else 1
    address_score = 1 if is_address and not identifier else 0
    return human_score, address_score, min(len(text), 120)


def _station_connector_codes(station: Mapping[str, Any]) -> set[str]:
    return {
        alias
        for item in station.get("connectors", [])
        if isinstance(item, Mapping) and item.get("code")
        for alias in _connector_code_aliases(item.get("code"))
    }


def _connector_code_aliases(value: Any) -> set[str]:
    """Return comparable aliases for compact and full eMI3 EVSE IDs."""
    source = str(value or "").strip().upper()
    compact = re.sub(r"[^A-Z0-9]", "", source)
    aliases = {compact} if compact else set()
    parts = [re.sub(r"[^A-Z0-9]", "", part) for part in source.split("*")]
    if len(parts) >= 3 and parts[-1]:
        suffix = parts[-1]
        aliases.add(suffix)
        if suffix.startswith("E") and len(suffix) > 10:
            aliases.add(suffix[1:])
    return aliases


def _station_spatial_cell(
    station: Mapping[str, Any],
) -> tuple[int, int] | None:
    """Return an approximately 100 metre spatial bucket."""
    try:
        latitude = float(station["latitude"])
        longitude = float(station["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    metres_per_degree = 111_320.0
    longitude_scale = max(abs(math.cos(math.radians(latitude))), 0.05)
    return (
        math.floor(latitude * metres_per_degree / 100.0),
        math.floor(longitude * metres_per_degree * longitude_scale / 100.0),
    )


def _same_physical_station(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> bool:
    first_codes = _station_connector_codes(first)
    second_codes = _station_connector_codes(second)
    if first_codes & second_codes:
        return True
    if first.get("provider") == second.get("provider"):
        return False
    try:
        distance = haversine_distance_m(
            float(first["latitude"]),
            float(first["longitude"]),
            float(second["latitude"]),
            float(second["longitude"]),
        )
    except (KeyError, TypeError, ValueError):
        return False
    if distance > 50:
        return False
    first_name = _normalized_station_identity(first.get("name"))
    second_name = _normalized_station_identity(second.get("name"))
    if len(first_name) >= 8 and first_name == second_name:
        return True
    first_address = _normalized_station_identity(first.get("address"))
    second_address = _normalized_station_identity(second.get("address"))
    if distance <= 25 and len(first_address) >= 12 and first_address == second_address:
        return True
    names_overlap = bool(
        min(len(first_name), len(second_name)) >= 8
        and (first_name in second_name or second_name in first_name)
    )
    addresses_overlap = bool(
        min(len(first_address), len(second_address)) >= 12
        and (first_address in second_address or second_address in first_address)
    )
    if distance <= 10 and names_overlap and addresses_overlap:
        return True
    first_operator = _normalized_operator(first.get("operator"))
    second_operator = _normalized_operator(second.get("operator"))
    return bool(
        distance <= 30
        and first_operator
        and first_operator == second_operator
    )


def _normalized_operator(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())
    if text in {"csdd", "emobi"}:
        return "emobi"
    return text


def _normalized_station_identity(value: Any) -> str:
    text = re.sub(r"^\s*\([^)]*\)\s*", "", str(value or "").casefold())
    return re.sub(r"[^\w]+", "", text, flags=re.UNICODE)


def _station_quality(station: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        1 if station.get("live_data_available") else 0,
        1 if station.get("connector_live_data_available") else 0,
        1
        if station.get("price_value") is not None
        or station.get("price_c_per_kwh") is not None
        else 0,
        1 if station.get("availability") not in {None, "", "unknown"} else 0,
        len(station.get("connectors", []))
        + (1 if station.get("provider") == "elektrum" else 0),
    )


def _provider_offer(station: Mapping[str, Any]) -> dict[str, Any]:
    """Keep one provider's independent price and live-data identity."""
    provider = str(station.get("provider") or "")
    provider_group = str(station.get("provider_group") or provider)
    return {
        "provider": provider,
        "provider_group": provider_group,
        "id": str(station.get("id") or ""),
        "operator": station.get("operator"),
        "description": station.get("description"),
        "descriptions": _merge_descriptions(
            station.get("descriptions"), station.get("description")
        ),
        "price_c_per_kwh": station.get("price_c_per_kwh"),
        "price_value": station.get("price_value"),
        "price_unit": station.get("price_unit"),
        "price_formatted": station.get("price_formatted"),
        "price_source": station.get("price_source"),
        "availability": station.get("availability", "unknown"),
        "available_connectors": station.get("available_connectors"),
        "occupied_connectors": station.get("occupied_connectors"),
        "live_data_available": bool(station.get("live_data_available")),
        "connector_live_data_available": bool(
            station.get("connector_live_data_available")
        ),
        "connectors": [
            dict(connector)
            for connector in station.get("connectors", [])
            if isinstance(connector, Mapping)
        ],
        "connector_count": station.get("connector_count"),
        "max_power_kw": station.get("max_power_kw"),
    }


def _merge_provider_offers(*sources: Any) -> list[dict[str, Any]]:
    """Retain the best independent offer for each user-facing provider."""
    offers_by_group: dict[str, dict[str, Any]] = {}
    order = {
        "elektrum": 0,
        "mobilly": 1,
        "emobi": 2,
        "nap": 3,
        "ignitis": 4,
        "ikrautas": 5,
    }
    for source in sources:
        if not isinstance(source, list):
            continue
        for value in source:
            if not isinstance(value, Mapping):
                continue
            offer = dict(value)
            group = str(offer.get("provider_group") or offer.get("provider") or "")
            if not group:
                continue
            offer["provider_group"] = group
            existing = offers_by_group.get(group)
            if existing is None:
                offers_by_group[group] = offer
                continue
            primary, secondary = (
                (offer, existing)
                if _offer_quality(offer) > _offer_quality(existing)
                else (existing, offer)
            )
            merged = dict(primary)
            merged["descriptions"] = _merge_descriptions(
                primary.get("descriptions"),
                primary.get("description"),
                secondary.get("descriptions"),
                secondary.get("description"),
            )
            if not merged.get("description") and merged["descriptions"]:
                merged["description"] = merged["descriptions"][0]
            merged["connectors"] = _merge_offer_connectors(
                primary.get("connectors"),
                secondary.get("connectors"),
            )
            merged["connector_count"] = len(merged["connectors"])
            powers = [
                _as_float(connector.get("power_kw"))
                for connector in merged["connectors"]
                if isinstance(connector, Mapping)
            ]
            merged["max_power_kw"] = max(
                (power for power in powers if power is not None),
                default=merged.get("max_power_kw"),
            )
            offers_by_group[group] = merged
    return sorted(
        offers_by_group.values(),
        key=lambda offer: (order.get(str(offer["provider_group"]), 99), str(offer["provider_group"])),
    )


def _merge_offer_connectors(*sources: Any) -> list[dict[str, Any]]:
    """Keep every physical connector while preferring richer live records."""
    result: list[dict[str, Any]] = []
    indexes: dict[str, int] = {}
    for source in sources:
        if not isinstance(source, list):
            continue
        for value in source:
            if not isinstance(value, Mapping):
                continue
            connector = dict(value)
            code = str(connector.get("code") or "").strip().casefold()
            if code:
                key = f"code:{code}"
            else:
                number = connector.get("connector_number") or connector.get(
                    "connector_index"
                )
                key = "fallback:{}|{}|{}".format(
                    number or f"anonymous-{len(result)}",
                    str(
                        connector.get("connector_type")
                        or connector.get("type")
                        or ""
                    ).casefold(),
                    connector.get("power_kw") or "",
                )
            existing_index = indexes.get(key)
            if existing_index is None:
                indexes[key] = len(result)
                result.append(connector)
                continue
            existing = result[existing_index]
            primary, secondary = (
                (connector, existing)
                if _connector_quality(connector) > _connector_quality(existing)
                else (existing, connector)
            )
            merged = dict(primary)
            for field, field_value in secondary.items():
                if merged.get(field) in (None, "", [], {}) and field_value not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    merged[field] = field_value
            result[existing_index] = merged
    return result


def _connector_quality(connector: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return (
        1 if connector.get("status") not in {None, "", "unknown"} else 0,
        1
        if connector.get("price_value") is not None
        or connector.get("price_c_per_kwh") is not None
        else 0,
        1 if connector.get("code") else 0,
        len(connector),
    )


def _offer_quality(offer: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        1 if offer.get("connector_live_data_available") else 0,
        1 if offer.get("live_data_available") else 0,
        1
        if offer.get("price_value") is not None
        or offer.get("price_c_per_kwh") is not None
        else 0,
        1 if offer.get("availability") not in {None, "", "unknown"} else 0,
        len(offer.get("connectors", [])),
    )


def _normalize_live_status(value: Any) -> str:
    """Map provider-specific live values to the dashboard status contract."""
    status = re.sub(r"[^a-z]", "", str(value or "").casefold())
    if status == "available":
        return "available"
    if status in OCCUPIED_STATUSES:
        return "occupied"
    if status in {"faulted", "inactive", "outoforder", "unavailable"}:
        return "unavailable"
    return "unknown"


def _operator_fallback_price(operator: str) -> dict[str, Any] | None:
    if operator.casefold() != "e-mobi":
        return None
    return {
        "price_c_per_kwh": None,
        "price_value": EMOBI_PRICE_C_PER_MIN,
        "price_unit": "min",
        "price_formatted": f"{EMOBI_PRICE_C_PER_MIN:.0f} c/min",
    }


def _unwrap_detail(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    current: Mapping[str, Any] = payload
    for key in ("data", "result", "site"):
        nested = current.get(key)
        if isinstance(nested, Mapping):
            current = nested
    return current


def _find_connector_records(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []
    for key in ("connectors", "chargingConnectors", "evses", "sockets"):
        items = value.get(key)
        if isinstance(items, list) and any(isinstance(item, Mapping) for item in items):
            return [item for item in items if isinstance(item, Mapping)]
    for key in ("chargingPoints", "points", "siteDetails", "details", "station"):
        nested = value.get(key)
        if isinstance(nested, list):
            found = [
                connector
                for item in nested
                if isinstance(item, Mapping)
                for connector in _find_connector_records(item)
            ]
            if found:
                return found
        elif isinstance(nested, Mapping):
            found = _find_connector_records(nested)
            if found:
                return found
    return []


def _match_connector(
    connectors: list[dict[str, Any]],
    raw: Mapping[str, Any],
    index: int,
) -> dict[str, Any] | None:
    code = str(_first_value(raw, "code", "evseId", "evse_id", "connectorId", "id") or "")
    if code:
        match = next(
            (item for item in connectors if str(item.get("code") or "") == code),
            None,
        )
        if match:
            return match
    return connectors[index] if index < len(connectors) else None


def _extract_price(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    formatted = _first_value(
        value, "priceFormatted", "price_formatted", "formattedPrice", "tariffText"
    )
    unit = _normalize_price_unit(
        _first_value(value, "priceUnit", "price_unit", "tariffUnit", "unit")
    )
    number = None
    is_eur = False
    for key in ("priceCents", "price_cents", "pricePerKwhCents", "pricePerMinuteCents"):
        if key in value:
            number = _as_float(value.get(key))
            break
    if number is None:
        for key in (
            "pricePerKwh",
            "price_per_kwh",
            "pricePerMinute",
            "price",
            "amount",
            "rate",
        ):
            if key in value:
                number = _as_float(_display_value(value.get(key)))
                is_eur = number is not None and number <= 5
                if "minute" in key.casefold() and unit is None:
                    unit = "min"
                if "kwh" in key.casefold() and unit is None:
                    unit = "kWh"
                break
    if formatted:
        text = str(formatted).replace(",", ".")
        if unit is None:
            unit = _normalize_price_unit(text)
        if number is None:
            match = re.search(r"(\d+(?:\.\d+)?)", text)
            if match:
                number = float(match.group(1))
                is_eur = "eur" in text.casefold() or "€" in text
    for key in ("tariff", "pricing", "rate", "chargingTariff"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            nested_price = _extract_price(nested)
            if nested_price:
                return nested_price
    if number is None:
        return None
    cents = round(number * 100 if is_eur else number, 4)
    unit = unit or "kWh"
    return {
        "price_c_per_kwh": cents if unit == "kWh" else None,
        "price_value": cents,
        "price_unit": unit,
        "price_formatted": str(formatted or f"{cents:g} c/{unit}"),
    }


def _lowest_connector_price(
    connectors: list[dict[str, Any]],
) -> dict[str, Any] | None:
    priced = [
        item for item in connectors if _as_float(item.get("price_value")) is not None
    ]
    if not priced:
        return None
    lowest = min(priced, key=lambda item: float(item["price_value"]))
    return {
        key: lowest.get(key)
        for key in ("price_c_per_kwh", "price_value", "price_unit", "price_formatted")
    }


def _normalize_price_unit(value: Any) -> str | None:
    text = str(_display_value(value) or "").casefold()
    if "min" in text:
        return "min"
    if "kwh" in text or "kw/h" in text:
        return "kWh"
    if "session" in text or "reize" in text:
        return "session"
    return None


def _first_value(value: Mapping[str, Any], *keys: str) -> Any:
    return next((value[key] for key in keys if value.get(key) is not None), None)


def _station_description(
    *sources: Any,
    language: str = "lv",
    exclude: tuple[Any, ...] = (),
) -> str | None:
    """Collect user-facing station notes without treating the address as a note."""
    fragments: list[str] = []
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in DESCRIPTION_KEYS:
            if key in source:
                fragments.extend(_description_fragments(source.get(key), language))
    excluded = {
        _normalized_description(value)
        for value in exclude
        if _normalized_description(value)
    }
    descriptions = _merge_descriptions(fragments)
    descriptions = [
        value for value in descriptions if _normalized_description(value) not in excluded
    ]
    return "\n".join(descriptions) or None


def _description_fragments(value: Any, language: str) -> list[str]:
    if isinstance(value, str):
        text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        return [
            line
            for raw_line in text.splitlines()
            if (line := re.sub(r"\s+", " ", raw_line).strip())
        ]
    if isinstance(value, (list, tuple, set)):
        return [
            fragment
            for item in value
            for fragment in _description_fragments(item, language)
        ]
    if not isinstance(value, Mapping):
        return []
    for key in (language, "en", "lv", "text", "value", "label", "description"):
        if key in value:
            fragments = _description_fragments(value.get(key), language)
            if fragments:
                return fragments
    return []


def _merge_descriptions(*sources: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for source in sources:
        values = source if isinstance(source, (list, tuple, set)) else [source]
        for value in values:
            if not isinstance(value, str):
                continue
            for line in value.splitlines():
                text = re.sub(r"\s+", " ", line).strip()
                normalized = _normalized_description(text)
                if not text or not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                result.append(text)
    return result


def _normalized_description(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _display_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value(value, "name", "value", "code", "label")
    return value


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _watts_to_kw(value: Any) -> float | None:
    number = _as_float(value)
    if number is None:
        return None
    return round(number / 1000 if number > 1000 else number, 3)


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
