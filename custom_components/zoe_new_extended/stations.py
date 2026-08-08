"""Authenticated Home Assistant HTTP views for charging-station maps."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from time import monotonic
from typing import Any

from aiohttp import ClientError, web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ZOE_LOCATION_ENTITY_ID
from .emobi_stations import EmobiStationsClient
from .mobilly_stations import MobillyStationsClient
from .stations_data import deduplicate_stations

VIEWS_REGISTERED = "_station_views_registered"
MOBILLY_CLIENT = "_mobilly_station_client"
EMOBI_CLIENT = "_emobi_station_client"
CATALOG_CACHE = "_station_catalog_cache"
CATALOG_REFRESH_TASK = "_station_catalog_refresh_task"
CATALOG_REFRESH_LOCK = "_station_catalog_refresh_lock"
CATALOG_CACHE_SECONDS = 2 * 60

_LOGGER = logging.getLogger(__name__)


async def _async_refresh_catalog(
    hass: HomeAssistant,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    domain_data = hass.data[DOMAIN]
    lock = domain_data.setdefault(CATALOG_REFRESH_LOCK, asyncio.Lock())
    async with lock:
        cached = domain_data.get(CATALOG_CACHE)
        if cached and monotonic() - cached[0] < CATALOG_CACHE_SECONDS:
            return cached[1]

        elektrum = runtime["elektrum_coordinator"]
        mobilly = domain_data[MOBILLY_CLIENT]
        emobi = domain_data[EMOBI_CLIENT]
        results = await asyncio.gather(
            elektrum.async_station_catalog(),
            mobilly.async_catalog(),
            emobi.async_catalog(),
            return_exceptions=True,
        )
        stations: list[dict[str, Any]] = []
        errors: dict[str, str] = {}
        for provider, result in zip(
            ("elektrum", "mobilly", "emobi"), results, strict=True
        ):
            if isinstance(result, Exception):
                errors[provider] = str(result)
            else:
                stations.extend(result)

        stations = await hass.async_add_executor_job(
            deduplicate_stations,
            stations,
        )
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "station_count": len(stations),
            "stations": stations,
            "errors": errors,
        }
        domain_data[CATALOG_CACHE] = (monotonic(), payload)
        return payload


def _ensure_catalog_refresh(
    hass: HomeAssistant,
    runtime: dict[str, Any],
) -> asyncio.Task[dict[str, Any]]:
    domain_data = hass.data[DOMAIN]
    task = domain_data.get(CATALOG_REFRESH_TASK)
    if task is None or task.done():
        task = hass.async_create_task(_async_refresh_catalog(hass, runtime))
        domain_data[CATALOG_REFRESH_TASK] = task
    return task


def _runtime(hass: HomeAssistant) -> dict[str, Any] | None:
    domain_data = hass.data.get(DOMAIN, {})
    return next(
        (
            value
            for value in domain_data.values()
            if isinstance(value, dict) and "elektrum_coordinator" in value
        ),
        None,
    )


def _vehicle_location(hass: HomeAssistant) -> dict[str, float] | None:
    state = hass.states.get(ZOE_LOCATION_ENTITY_ID)
    if state is None:
        return None
    try:
        return {
            "latitude": float(state.attributes[ATTR_LATITUDE]),
            "longitude": float(state.attributes[ATTR_LONGITUDE]),
        }
    except (KeyError, TypeError, ValueError):
        return None


class ZoeNewStationsView(HomeAssistantView):
    """Return public Elektrum, Mobilly, and e-mobi station catalogs."""

    url = "/api/zoe_new_extended/stations"
    name = "api:zoe_new_extended:stations"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        runtime = _runtime(hass)
        if runtime is None:
            return self.json({"error": "Integration is not loaded"}, status_code=503)

        domain_data = hass.data[DOMAIN]
        cached = domain_data.get(CATALOG_CACHE)
        if cached is None:
            catalog = await _ensure_catalog_refresh(hass, runtime)
        else:
            catalog = cached[1]
            if monotonic() - cached[0] >= CATALOG_CACHE_SECONDS:
                _ensure_catalog_refresh(hass, runtime)
        return self.json(
            {
                **catalog,
                "vehicle_location": _vehicle_location(hass),
            }
        )


class ZoeNewStationDetailView(HomeAssistantView):
    """Return live or public detail for one selected station."""

    url = "/api/zoe_new_extended/stations/{provider}/{station_id}"
    name = "api:zoe_new_extended:station_detail"
    requires_auth = True

    async def get(
        self,
        request: web.Request,
        provider: str,
        station_id: str,
    ) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        runtime = _runtime(hass)
        if runtime is None:
            return self.json({"error": "Integration is not loaded"}, status_code=503)

        try:
            if provider == "elektrum":
                detail = await runtime[
                    "elektrum_coordinator"
                ].async_station_detail(station_id)
            elif provider == "mobilly":
                detail = await hass.data[DOMAIN][MOBILLY_CLIENT].async_detail(
                    station_id
                )
            elif provider in {"emobi", "emobi_elektrum"}:
                detail = await hass.data[DOMAIN][EMOBI_CLIENT].async_detail(station_id)
            else:
                return self.json({"error": "Unknown provider"}, status_code=400)
        except (ClientError, RuntimeError, TimeoutError, ValueError) as err:
            _LOGGER.warning(
                "Unable to fetch %s charging station %s: %s",
                provider,
                station_id,
                err,
            )
            return self.json(
                {"error": "Live station data is temporarily unavailable"},
                status_code=502,
            )

        if detail is None:
            return self.json({"error": "Station not found"}, status_code=404)
        return self.json(detail)


def async_register_station_views(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Register singleton station views and their shared Mobilly cache."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(VIEWS_REGISTERED):
        return
    domain_data[MOBILLY_CLIENT] = MobillyStationsClient(hass, entry)
    domain_data[EMOBI_CLIENT] = EmobiStationsClient(hass)
    hass.http.register_view(ZoeNewStationsView())
    hass.http.register_view(ZoeNewStationDetailView())
    domain_data[VIEWS_REGISTERED] = True
    runtime = _runtime(hass)
    if runtime is not None:
        warm_task = _ensure_catalog_refresh(hass, runtime)

        def cancel_warm_task() -> None:
            warm_task.cancel()

        entry.async_on_unload(cancel_warm_task)
