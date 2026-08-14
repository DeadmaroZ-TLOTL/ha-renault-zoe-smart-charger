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
from homeassistant.helpers.storage import Store

from .ampeco_stations import ignitis_on_client, ikrautas_client
from .const import DOMAIN, ZOE_LOCATION_ENTITY_ID
from .emobi_stations import EmobiStationsClient
from .latvia_nap_stations import LatviaNapStationsClient
from .mobilly_stations import MobillyStationsClient
from .stations_data import deduplicate_stations

VIEWS_REGISTERED = "_station_views_registered"
MOBILLY_CLIENT = "_mobilly_station_client"
EMOBI_CLIENT = "_emobi_station_client"
LATVIA_NAP_CLIENT = "_latvia_nap_station_client"
IGNITIS_CLIENT = "_ignitis_on_station_client"
IKRAUTAS_CLIENT = "_ikrautas_station_client"
CATALOG_CACHE = "_station_catalog_cache"
CATALOG_REFRESH_TASK = "_station_catalog_refresh_task"
CATALOG_REFRESH_LOCK = "_station_catalog_refresh_lock"
CATALOG_SOURCE_CACHE = "_station_source_catalog_cache"
CATALOG_SOURCE_CACHE_LOADED = "_station_source_catalog_cache_loaded"
CATALOG_STORE = "_station_catalog_store"
CATALOG_CACHE_SECONDS = 2 * 60
CATALOG_STORE_VERSION = 1

_LOGGER = logging.getLogger(__name__)


async def _async_load_source_cache(domain_data: dict[str, Any]) -> None:
    """Restore the last complete provider catalogs once per HA start."""
    if domain_data.get(CATALOG_SOURCE_CACHE_LOADED):
        return
    domain_data[CATALOG_SOURCE_CACHE_LOADED] = True
    source_cache: dict[str, dict[str, Any]] = {}
    try:
        payload = await domain_data[CATALOG_STORE].async_load()
    except (OSError, ValueError, TypeError) as err:
        _LOGGER.warning("Unable to load charging-station cache: %s", err)
        payload = None
    providers = payload.get("providers") if isinstance(payload, dict) else None
    if isinstance(providers, dict):
        for provider, value in providers.items():
            if not isinstance(value, dict) or not isinstance(
                value.get("stations"), list
            ):
                continue
            source_cache[str(provider)] = {
                "stations": [
                    dict(station)
                    for station in value["stations"]
                    if isinstance(station, dict)
                ],
                "stats": (
                    dict(value["stats"])
                    if isinstance(value.get("stats"), dict)
                    else {}
                ),
                "saved_at": value.get("saved_at"),
            }
    domain_data[CATALOG_SOURCE_CACHE] = source_cache


async def _async_save_source_cache(domain_data: dict[str, Any]) -> None:
    """Persist public station data without account or authentication data."""
    try:
        await domain_data[CATALOG_STORE].async_save(
            {
                "providers": domain_data.get(CATALOG_SOURCE_CACHE, {}),
                "saved_at": datetime.now(UTC).isoformat(),
            }
        )
    except (OSError, ValueError, TypeError) as err:
        _LOGGER.warning("Unable to save charging-station cache: %s", err)


async def _async_refresh_catalog(
    hass: HomeAssistant,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    domain_data = hass.data[DOMAIN]
    lock = domain_data.setdefault(CATALOG_REFRESH_LOCK, asyncio.Lock())
    async with lock:
        await _async_load_source_cache(domain_data)
        cached = domain_data.get(CATALOG_CACHE)
        if cached and monotonic() - cached[0] < CATALOG_CACHE_SECONDS:
            return cached[1]

        elektrum = runtime["elektrum_coordinator"]
        mobilly = domain_data[MOBILLY_CLIENT]
        emobi = domain_data[EMOBI_CLIENT]
        latvia_nap = domain_data[LATVIA_NAP_CLIENT]
        ignitis = domain_data[IGNITIS_CLIENT]
        ikrautas = domain_data[IKRAUTAS_CLIENT]
        results = await asyncio.gather(
            elektrum.async_station_catalog(),
            mobilly.async_catalog(),
            emobi.async_catalog(),
            latvia_nap.async_catalog(),
            ignitis.async_catalog(),
            ikrautas.async_catalog(),
            return_exceptions=True,
        )
        stations: list[dict[str, Any]] = []
        errors: dict[str, str] = {}
        source_counts: dict[str, int] = {}
        source_details: dict[str, dict[str, Any]] = {}
        fallback_sources: dict[str, dict[str, Any]] = {}
        source_cache = domain_data[CATALOG_SOURCE_CACHE]
        providers = (
            "elektrum",
            "mobilly",
            "emobi",
            "latvia_nap",
            "ignitis",
            "ikrautas",
        )
        clients = (elektrum, mobilly, emobi, latvia_nap, ignitis, ikrautas)
        cache_changed = False
        generated_at = datetime.now(UTC).isoformat()
        for provider, client, result in zip(
            providers,
            clients,
            results,
            strict=True,
        ):
            provider_error = result if isinstance(result, Exception) else None
            provider_stations = result if isinstance(result, list) else []
            if not provider_stations and provider_error is None:
                provider_error = RuntimeError("provider returned an empty catalog")

            if provider_error is not None:
                errors[provider] = str(provider_error)
                fallback = source_cache.get(provider, {})
                fallback_stations = fallback.get("stations")
                if isinstance(fallback_stations, list) and fallback_stations:
                    provider_stations = [
                        dict(station)
                        for station in fallback_stations
                        if isinstance(station, dict)
                    ]
                    source_details[provider] = dict(fallback.get("stats") or {})
                    fallback_sources[provider] = {
                        "station_count": len(provider_stations),
                        "saved_at": fallback.get("saved_at"),
                    }
                else:
                    provider_stations = []
                    source_details[provider] = {}
            else:
                stats = dict(client.catalog_stats)
                source_details[provider] = stats
                source_cache[provider] = {
                    "stations": [dict(station) for station in provider_stations],
                    "stats": stats,
                    "saved_at": generated_at,
                }
                cache_changed = True

            source_counts[provider] = len(provider_stations)
            stations.extend(provider_stations)

        if cache_changed:
            await _async_save_source_cache(domain_data)

        source_station_count = len(stations)
        stations = await hass.async_add_executor_job(
            deduplicate_stations,
            stations,
        )
        payload = {
            "generated_at": generated_at,
            "station_count": len(stations),
            "source_station_count": source_station_count,
            "duplicates_collapsed": source_station_count - len(stations),
            "source_counts": source_counts,
            "source_details": source_details,
            "fallback_sources": fallback_sources,
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
    """Return public provider and Latvia NAP station catalogs."""

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
            elif provider == "latvia_nap":
                detail = await hass.data[DOMAIN][LATVIA_NAP_CLIENT].async_detail(
                    station_id
                )
            elif provider == "ignitis_on":
                detail = await hass.data[DOMAIN][IGNITIS_CLIENT].async_detail(
                    station_id
                )
            elif provider == "ikrautas":
                detail = await hass.data[DOMAIN][IKRAUTAS_CLIENT].async_detail(
                    station_id
                )
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
    """Register station views and bind clients to the current config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    # Options updates reload the config entry, but the HTTP views remain
    # registered for the lifetime of Home Assistant. Rebind account-aware
    # clients on every setup so newly authenticated sessions are used at once.
    domain_data[MOBILLY_CLIENT] = MobillyStationsClient(hass, entry)
    domain_data[EMOBI_CLIENT] = EmobiStationsClient(hass)
    domain_data[LATVIA_NAP_CLIENT] = LatviaNapStationsClient(hass)
    domain_data[IGNITIS_CLIENT] = ignitis_on_client(hass, entry)
    domain_data[IKRAUTAS_CLIENT] = ikrautas_client(hass, entry)
    domain_data.pop(CATALOG_CACHE, None)
    previous_refresh = domain_data.pop(CATALOG_REFRESH_TASK, None)
    if previous_refresh is not None and not previous_refresh.done():
        previous_refresh.cancel()

    if domain_data.get(VIEWS_REGISTERED):
        runtime = _runtime(hass)
        if runtime is not None:
            warm_task = _ensure_catalog_refresh(hass, runtime)

            def cancel_reloaded_warm_task() -> None:
                warm_task.cancel()

            entry.async_on_unload(cancel_reloaded_warm_task)
        return

    domain_data[CATALOG_STORE] = Store(
        hass,
        CATALOG_STORE_VERSION,
        f"{DOMAIN}.station_catalog_sources",
    )
    hass.http.register_view(ZoeNewStationsView())
    hass.http.register_view(ZoeNewStationDetailView())
    domain_data[VIEWS_REGISTERED] = True
    runtime = _runtime(hass)
    if runtime is not None:
        warm_task = _ensure_catalog_refresh(hass, runtime)

        def cancel_warm_task() -> None:
            warm_task.cancel()

        entry.async_on_unload(cancel_warm_task)
