"""Pure DATEX II helpers for Latvia's National Access Point EV feeds."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree


ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {"transportdata.gov.lv", "www.transportdata.gov.lv"}
)
OCCUPIED_STATUSES = frozenset(
    {
        "blocked",
        "charging",
        "finishing",
        "occupied",
        "preparing",
        "reserved",
        "suspendedev",
        "suspendedevse",
    }
)
UNAVAILABLE_STATUSES = frozenset(
    {"faulted", "inactive", "inoperative", "outoforder", "unavailable"}
)
CONNECTOR_NAMES = {
    "chademo": "CHAdeMO",
    "domestic": "Schuko",
    "iec62196t1": "Type 1",
    "iec62196t1combo": "CCS (Type 1)",
    "iec62196t2": "Type 2",
    "iec62196t2combo": "CCS (Type 2)",
    "tesla": "Tesla",
}


def current_download_url(metadata: Mapping[str, Any]) -> str:
    """Return and validate the newest rotating NAP data-file URL."""
    candidates: list[tuple[int, str]] = []
    records = metadata.get("field_download_url")
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, Mapping):
                continue
            files = record.get("field_file")
            if not isinstance(files, list):
                continue
            for item in files:
                if not isinstance(item, Mapping) or not item.get("url"):
                    continue
                try:
                    identifier = int(item.get("fid") or 0)
                except (TypeError, ValueError):
                    identifier = 0
                candidates.append((identifier, str(item["url"])))
    if not candidates:
        raise ValueError("Latvia NAP metadata does not contain a current file")
    url = max(candidates, key=lambda item: item[0])[1]
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS
        or not parsed.path.startswith("/npp-test/")
    ):
        raise ValueError("Latvia NAP metadata returned an unexpected file URL")
    return url


def parse_latvia_nap_catalog(
    infrastructure_xml: bytes,
    status_xml: bytes,
) -> list[dict[str, Any]]:
    """Join static infrastructure with live status and price DATEX feeds."""
    infrastructure_root = ElementTree.fromstring(infrastructure_xml)
    status_root = ElementTree.fromstring(status_xml)
    live_by_reference = _parse_live_status(status_root)
    stations: list[dict[str, Any]] = []
    for site in _descendants(infrastructure_root, "energyInfrastructureSite"):
        normalized = _normalize_site(site, live_by_reference)
        if normalized is not None:
            stations.append(normalized)
    return stations


def _parse_live_status(root: ElementTree.Element) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for site_status in _descendants(root, "energyInfrastructureSiteStatus"):
        site_id = _reference_id(site_status)
        site_updated = _child_text(site_status, "lastUpdated")
        site_records: list[dict[str, Any]] = []
        for station_status in _children(
            site_status, "energyInfrastructureStationStatus"
        ):
            station_id = _reference_id(station_status)
            updated = _child_text(station_status, "lastUpdated") or site_updated
            price = _price_from_status(station_status)
            refill_statuses = _children(station_status, "refillPointStatus")
            if not refill_statuses:
                refill_statuses = [station_status]
            for refill_status in refill_statuses:
                external_id = _reference_id(refill_status)
                record = {
                    "status": _normalize_status(
                        _child_text(refill_status, "status")
                    ),
                    "status_observed_since": updated,
                    **price,
                }
                site_records.append(record)
                for reference in (station_id, external_id):
                    if reference:
                        result[reference] = record
        if site_id:
            result[site_id] = {
                "status_observed_since": site_updated,
                "records": site_records,
            }
    return result


def _normalize_site(
    site: ElementTree.Element,
    live_by_reference: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    site_id = str(site.attrib.get("id") or "").strip()
    latitude = _as_float(_descendant_text(site, "latitude"))
    longitude = _as_float(_descendant_text(site, "longitude"))
    if not site_id or latitude is None or longitude is None:
        return None

    name = _localized_value(_child(site, "name")) or site_id
    operator_element = _child(site, "operator")
    operator = _localized_value(_child(operator_element, "name")) or "Unknown"
    address_element = _descendant(site, "address")
    city = _child_text(address_element, "city")
    country = _child_text(address_element, "countryCode") or "LV"
    postcode = _child_text(address_element, "postcode")
    address = next(
        (
            _child_text(line, "text")
            for line in _children(address_element, "addressLine")
            if _child_text(line, "type") == "street"
            and _child_text(line, "text")
        ),
        None,
    )

    connectors: list[dict[str, Any]] = []
    live_connector_count = 0
    for refill_index, refill_point in enumerate(
        _descendants(site, "refillPoint"), start=1
    ):
        refill_id = str(refill_point.attrib.get("id") or "").strip()
        external_id = _child_text(refill_point, "externalIdentifier") or refill_id
        live = live_by_reference.get(refill_id) or live_by_reference.get(external_id)
        live = live or {}
        if live:
            live_connector_count += 1
        raw_connectors = _children(refill_point, "connector")
        for connector_index, raw_connector in enumerate(raw_connectors, start=1):
            connector_type = _child_text(raw_connector, "connectorType")
            power_watts = _as_float(
                _child_text(raw_connector, "maxPowerAtSocket")
            )
            charging_mode = _child_text(raw_connector, "chargingMode")
            connector = {
                "code": external_id,
                "connector_type": _connector_name(connector_type),
                "datex_connector_type": connector_type,
                "power_kw": (
                    round(power_watts / 1000, 3)
                    if power_watts is not None
                    else None
                ),
                "current_type": (
                    "DC" if str(charging_mode or "").casefold().endswith("dc") else "AC"
                ),
                "connector_index": len(connectors) + 1,
                "connector_number": refill_index,
                "socket_index": connector_index,
                "status": live.get("status", "unknown"),
                "status_observed_since": live.get("status_observed_since"),
            }
            connector.update(_price_fields(live))
            connectors.append(connector)

    site_live = live_by_reference.get(site_id) or {}
    if not connectors and isinstance(site_live.get("records"), list):
        statuses = [
            str(record.get("status") or "unknown")
            for record in site_live["records"]
            if isinstance(record, Mapping)
        ]
    else:
        statuses = [str(item.get("status") or "unknown") for item in connectors]
    available = statuses.count("available")
    occupied = statuses.count("occupied")
    unavailable = statuses.count("unavailable")
    price = _lowest_price(connectors)
    description_parts = [part for part in (postcode, city) if part]
    result: dict[str, Any] = {
        "provider": "latvia_nap",
        "provider_group": "nap",
        "id": site_id,
        "name": name,
        "description": ", ".join(description_parts) or None,
        "descriptions": [],
        "address": address,
        "city": city,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "partner": True,
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
            if unavailable and unavailable == len(statuses)
            else "unknown"
        ),
        "available_connectors": available if live_connector_count else None,
        "occupied_connectors": occupied if live_connector_count else None,
        "live_data_available": bool(live_connector_count),
        "connector_live_data_available": bool(live_connector_count),
        "status_source": "latvia_nap_ecomovement",
        "detail_source": "latvia_nap_ecomovement",
        "status_observed_since": site_live.get("status_observed_since"),
    }
    if price:
        result.update(price)
        result["price_source"] = "latvia_nap_ecomovement"
    return result


def _price_from_status(element: ElementTree.Element) -> dict[str, Any]:
    prices: list[float] = []
    for rate_line in _descendants(element, "rateLine"):
        if (_child_text(rate_line, "rateLineType") or "").casefold() != "perunit":
            continue
        value = _as_float(_child_text(rate_line, "value"))
        # Zero is used by some records when no public tariff was supplied.
        if value is None or value <= 0:
            continue
        tax_rate = _as_float(_descendant_text(rate_line, "taxRate")) or 0.0
        tax_included = (_descendant_text(rate_line, "taxIncluded") or "").casefold()
        gross = value if tax_included == "true" else value * (1 + tax_rate / 100)
        prices.append(round(gross * 100, 4))
    if not prices:
        return {}
    unique_prices = sorted(set(prices))
    lowest = unique_prices[0]
    formatted = (
        f"{lowest:g} c/kWh"
        if len(unique_prices) == 1
        else f"{lowest:g}-{unique_prices[-1]:g} c/kWh"
    )
    return {
        "price_c_per_kwh": lowest,
        "price_value": lowest,
        "price_unit": "kWh",
        "price_formatted": formatted,
        "price_options_c_per_kwh": unique_prices,
        "price_source": "latvia_nap_ecomovement",
    }


def _price_fields(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value[key]
        for key in (
            "price_c_per_kwh",
            "price_value",
            "price_unit",
            "price_formatted",
            "price_options_c_per_kwh",
            "price_source",
        )
        if key in value
    }


def _lowest_price(connectors: list[dict[str, Any]]) -> dict[str, Any] | None:
    priced = [item for item in connectors if item.get("price_value") is not None]
    if not priced:
        return None
    return _price_fields(min(priced, key=lambda item: float(item["price_value"])))


def _normalize_status(value: Any) -> str:
    status = "".join(
        character
        for character in str(value or "").casefold()
        if character.isalpha()
    )
    if status == "available":
        return "available"
    if status in OCCUPIED_STATUSES:
        return "occupied"
    if status in UNAVAILABLE_STATUSES:
        return "unavailable"
    return "unknown"


def _connector_name(value: Any) -> str:
    raw = str(value or "Unknown").strip()
    normalized = "".join(
        character for character in raw.casefold() if character.isalnum()
    )
    return CONNECTOR_NAMES.get(normalized, raw)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(
    element: ElementTree.Element | None, name: str
) -> list[ElementTree.Element]:
    if element is None:
        return []
    return [child for child in element if _local_name(child.tag) == name]


def _child(
    element: ElementTree.Element | None, name: str
) -> ElementTree.Element | None:
    return next(iter(_children(element, name)), None)


def _descendants(
    element: ElementTree.Element | None, name: str
) -> list[ElementTree.Element]:
    if element is None:
        return []
    return [item for item in element.iter() if _local_name(item.tag) == name]


def _descendant(
    element: ElementTree.Element | None, name: str
) -> ElementTree.Element | None:
    return next(iter(_descendants(element, name)), None)


def _element_text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _child_text(element: ElementTree.Element | None, name: str) -> str | None:
    return _element_text(_child(element, name))


def _descendant_text(element: ElementTree.Element | None, name: str) -> str | None:
    return _element_text(_descendant(element, name))


def _localized_value(element: ElementTree.Element | None) -> str | None:
    values = _descendants(element, "value")
    preferred = next(
        (item for item in values if item.attrib.get("lang") in {"en", "lv"}),
        None,
    )
    selected = preferred if preferred is not None else next(iter(values), None)
    return _element_text(selected)


def _reference_id(element: ElementTree.Element | None) -> str | None:
    reference = _child(element, "reference")
    if reference is None:
        return None
    value = str(reference.attrib.get("id") or "").strip()
    return value or None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
