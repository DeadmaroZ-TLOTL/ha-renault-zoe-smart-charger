"""Device helpers for Zoe New Extended entity grouping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


@dataclass(frozen=True)
class SourceDevice:
    """Describe one Home Assistant device used for a logical data source."""

    slug: str
    label: str
    manufacturer: str
    model: str


SOURCE_ZOE_API = SourceDevice(
    slug="zoe_new_api",
    label="Zoe New API",
    manufacturer="Renault",
    model="Zoe New API",
)
SOURCE_IMMAX = SourceDevice(
    slug="immax",
    label="IMMAX",
    manufacturer="IMMAX",
    model="Smart charger proxy",
)
SOURCE_SMART_CHARGING = SourceDevice(
    slug="smart_charging",
    label="Smart Charging",
    manufacturer="Zoe New Extended",
    model="Charging planner",
)
SOURCE_CHARGING_ACCOUNTS = SourceDevice(
    slug="charging_accounts",
    label="Charging Accounts",
    manufacturer="Zoe New Extended",
    model="Mobilly and Elektrum Drive",
)
SOURCE_NORDPOOL = SourceDevice(
    slug="nordpool",
    label="Nord Pool",
    manufacturer="Nord Pool",
    model="Energy price source",
)


def _value(obj: Any, name: str) -> Any:
    """Return an attribute or mapping value without assuming its shape."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def vehicle_vin(vehicle: Any) -> str:
    """Return the vehicle VIN used for stable source-device identifiers."""
    details = getattr(vehicle, "details", None)
    vin = _value(details, "vin") or _value(vehicle, "vin")
    return str(vin or "unknown").lower()


def _vehicle_name(vehicle: Any) -> str:
    """Return a friendly vehicle name for child source devices."""
    device_info = getattr(vehicle, "device_info", None) or {}
    for candidate in (
        _value(device_info, "name"),
        _value(getattr(vehicle, "details", None), "nickname"),
        _value(getattr(vehicle, "details", None), "registration_number"),
    ):
        if candidate:
            return str(candidate)
    vin = vehicle_vin(vehicle)
    return f"Renault Zoe {vin[-6:].upper()}" if vin != "unknown" else "Renault Zoe"


def vehicle_device_identifier(vehicle: Any) -> tuple[str, str] | None:
    """Return one identifier for the original Renault vehicle device."""
    device_info = getattr(vehicle, "device_info", None) or {}
    identifiers = _value(device_info, "identifiers") or ()
    for identifier in identifiers:
        if len(identifier) == 2:
            return tuple(identifier)
    vin = vehicle_vin(vehicle)
    if vin == "unknown":
        return None
    return ("renault", vin)


def source_device_identifier(
    vehicle: Any, source: SourceDevice
) -> tuple[str, str]:
    """Return the stable identifier for one logical source device."""
    return (DOMAIN, f"{vehicle_vin(vehicle)}_{source.slug}")


def source_device_info(vehicle: Any, source: SourceDevice) -> DeviceInfo:
    """Build DeviceInfo without copying Renault identifiers or connections."""
    info: DeviceInfo = {
        "identifiers": {source_device_identifier(vehicle, source)},
        "name": f"{_vehicle_name(vehicle)} {source.label}",
        "manufacturer": source.manufacturer,
        "model": source.model,
    }
    if via_device := vehicle_device_identifier(vehicle):
        info["via_device"] = via_device
    return info
