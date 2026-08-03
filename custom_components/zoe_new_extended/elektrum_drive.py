"""Elektrum Drive station matching and current public tariff coordinator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from time import monotonic
from typing import Any

from aiohttp import ClientError, ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_ELEKTRUM_DRIVE_ENABLED,
    CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
    DEFAULT_ELEKTRUM_DRIVE_ENABLED,
    DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
    ZOE_LOCATION_ENTITY_ID,
)
from .elektrum_drive_data import (
    nearest_station,
    parse_connector_page,
    price_after_discount,
    select_connector,
    station_connectors,
    station_coordinates,
)

_LOGGER = logging.getLogger(__name__)

STATIONS_URL = "https://www.elektrum.lv/api/electro-car-charging-stations"
DIRECT_CONNECTOR_URL = "https://direct.elektrumdrive.com/lv/qr"
UPDATE_INTERVAL = timedelta(minutes=2)
STATION_CACHE_SECONDS = 6 * 60 * 60
MATCH_RADIUS_M = 300.0
REQUEST_TIMEOUT = ClientTimeout(total=25)
REQUEST_HEADERS = {
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (compatible; HomeAssistant ZoeNewExtended/1.12)"
    ),
}


class ElektrumDriveCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Match the Zoe location to Elektrum and read its current tariff."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Renault Zoe New Elektrum Drive",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self._stations: list[dict[str, Any]] = []
        self._stations_loaded_at = 0.0

    @property
    def enabled(self) -> bool:
        """Return whether Elektrum matching is enabled."""
        return bool(
            self.entry.options.get(
                CONF_ELEKTRUM_DRIVE_ENABLED,
                DEFAULT_ELEKTRUM_DRIVE_ENABLED,
            )
        )

    @property
    def discount_percent(self) -> float:
        """Return the configured Elektrum own-network postpaid discount."""
        return float(
            self.entry.options.get(
                CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
                DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
            )
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Resolve the current station, connector, and tariff."""
        fetched_at = datetime.now(UTC).isoformat()
        if not self.enabled:
            return self._empty_data(fetched_at, enabled=False)

        tracker = self.hass.states.get(ZOE_LOCATION_ENTITY_ID)
        latitude = _as_float(tracker.attributes.get(ATTR_LATITUDE)) if tracker else None
        longitude = _as_float(tracker.attributes.get(ATTR_LONGITUDE)) if tracker else None
        if latitude is None or longitude is None:
            return self._empty_data(
                fetched_at,
                error="Renault location is unavailable",
            )

        station_error = None
        try:
            await self._async_ensure_stations()
        except (ClientError, TimeoutError, ValueError) as err:
            station_error = str(err)
            _LOGGER.warning("Unable to refresh Elektrum Drive stations: %s", err)
        if not self._stations:
            return self._empty_data(
                fetched_at,
                latitude=latitude,
                longitude=longitude,
                error=station_error or "Elektrum Drive returned no stations",
            )

        station, distance = nearest_station(self._stations, latitude, longitude)
        if station is None or distance is None:
            return self._empty_data(
                fetched_at,
                latitude=latitude,
                longitude=longitude,
                error="Elektrum Drive returned no geocoded stations",
            )

        matched = distance <= MATCH_RADIUS_M
        base_data = self._station_data(
            station,
            distance,
            latitude,
            longitude,
            fetched_at,
            matched=matched,
        )
        if not matched:
            base_data["station_refresh_error"] = station_error
            return base_data

        public_connectors = station_connectors(station)
        results = await asyncio.gather(
            *(self._async_fetch_connector(item["code"]) for item in public_connectors),
            return_exceptions=True,
        )
        connectors = []
        connector_errors = []
        for public, result in zip(public_connectors, results, strict=True):
            if isinstance(result, Exception):
                connector_errors.append(f"{public['code']}: {result}")
                connectors.append(dict(public))
                continue
            connectors.append({**public, **result})

        selected = select_connector(
            connectors,
            is_charging=_is_charging(self.hass),
            observed_power_kw=_observed_power_kw(self.hass),
        )
        direct_price = (
            _as_float(selected.get("price_c_per_kwh")) if selected else None
        )
        partner = bool(station.get("partner"))
        applied_discount = 0.0 if partner else self.discount_percent
        final_price = price_after_discount(
            direct_price,
            partner=partner,
            discount_percent=self.discount_percent,
        )
        base_data.update(
            {
                "connectors": connectors,
                "selected_connector": selected,
                "connector_code": selected.get("code") if selected else None,
                "connector_status": selected.get("status") if selected else None,
                "connector_type": (
                    selected.get("connector_type") if selected else None
                ),
                "connector_power_kw": (
                    selected.get("power_kw") if selected else None
                ),
                "direct_price_c_per_kwh": direct_price,
                "price_c_per_kwh": final_price,
                "postpaid_discount_percent": applied_discount,
                "configured_discount_percent": self.discount_percent,
                "vat_included": True,
                "price_source": "elektrum_drive_direct",
                "price_url": (
                    f"{DIRECT_CONNECTOR_URL}?evseid={selected['code']}"
                    if selected
                    else None
                ),
                "connector_errors": connector_errors,
                "station_refresh_error": station_error,
            }
        )
        return base_data

    async def _async_ensure_stations(self) -> None:
        """Refresh the large public station list at most every six hours."""
        if (
            self._stations
            and monotonic() - self._stations_loaded_at < STATION_CACHE_SECONDS
        ):
            return
        session = async_get_clientsession(self.hass)
        async with session.get(
            STATIONS_URL,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        if not isinstance(payload, list):
            raise ValueError("Elektrum Drive station response is not a list")
        self._stations = [item for item in payload if isinstance(item, dict)]
        self._stations_loaded_at = monotonic()

    async def _async_fetch_connector(self, code: str) -> dict[str, Any]:
        """Fetch one server-rendered Direct connector page."""
        session = async_get_clientsession(self.hass)
        async with session.get(
            DIRECT_CONNECTOR_URL,
            params={"evseid": code},
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            page = await response.text()
        return parse_connector_page(page)

    @staticmethod
    def _station_data(
        station: dict[str, Any],
        distance: float,
        latitude: float,
        longitude: float,
        fetched_at: str,
        *,
        matched: bool,
    ) -> dict[str, Any]:
        coordinates = station_coordinates(station)
        address = station.get("address")
        city = station.get("city")
        display_name = ", ".join(str(item) for item in (address, city) if item)
        return {
            "enabled": True,
            "location_available": True,
            "matched": matched,
            "match_radius_m": MATCH_RADIUS_M,
            "distance_m": round(distance, 1),
            "station_id": station.get("id"),
            "station_name": display_name or station.get("name"),
            "station_address": address,
            "station_city": city,
            "station_partner": bool(station.get("partner")),
            "station_latitude": coordinates[0] if coordinates else None,
            "station_longitude": coordinates[1] if coordinates else None,
            "vehicle_latitude": latitude,
            "vehicle_longitude": longitude,
            "connectors": station_connectors(station),
            "selected_connector": None,
            "price_c_per_kwh": None,
            "fetched_at": fetched_at,
        }

    @staticmethod
    def _empty_data(
        fetched_at: str,
        *,
        enabled: bool = True,
        latitude: float | None = None,
        longitude: float | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        return {
            "enabled": enabled,
            "location_available": latitude is not None and longitude is not None,
            "matched": False,
            "match_radius_m": MATCH_RADIUS_M,
            "vehicle_latitude": latitude,
            "vehicle_longitude": longitude,
            "station_id": None,
            "station_name": None,
            "station_partner": None,
            "connectors": [],
            "selected_connector": None,
            "price_c_per_kwh": None,
            "error": error,
            "fetched_at": fetched_at,
        }


def _is_charging(hass: HomeAssistant) -> bool:
    for entity_id in ("binary_sensor.charging", "binary_sensor.plug"):
        binary_state = hass.states.get(entity_id)
        if binary_state is not None and binary_state.state == "on":
            return True
    for entity_id in (
        "sensor.renault_zoe_new_raw_charge_status",
        "sensor.charge_state",
        "sensor.plug_state",
    ):
        status = hass.states.get(entity_id)
        if status is not None and status.state.lower() in {
            "charge_in_progress",
            "charging",
            "connected",
            "plugged",
            "plugged_in",
        }:
            return True
    return False


def _observed_power_kw(hass: HomeAssistant) -> float | None:
    for entity_id in (
        "sensor.zoe_active_charging_power",
        "sensor.zoe_calculated_charging_power",
    ):
        state = hass.states.get(entity_id)
        value = _as_float(state.state) if state else None
        if value is not None and value > 0:
            return value
    return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
