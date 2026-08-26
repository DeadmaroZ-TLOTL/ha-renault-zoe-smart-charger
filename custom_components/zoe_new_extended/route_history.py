"""Retain genuine Renault GPS points beyond Recorder's raw-state window."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import DOMAIN, ZOE_LOCATION_ENTITY_ID
from .route_history_data import normalize_route_points

_LOGGER = logging.getLogger(__name__)

ROUTE_HISTORY_STORE_VERSION = 1
ROUTE_HISTORY_STORE = "_route_history_store"
ROUTE_HISTORY_CACHE = "_route_history_cache"
ROUTE_HISTORY_LOCK = "_route_history_lock"
ROUTE_HISTORY_VIEW_REGISTERED = "_route_history_view_registered"
MAX_ROUTE_HISTORY_BATCH_POINTS = 100_000


def _point_from_state(state: State | None) -> dict[str, Any] | None:
    """Convert a Renault location state to a retained route point."""
    if state is None:
        return None
    attributes = state.attributes
    timestamp = state.last_updated.timestamp() * 1000
    raw_point: dict[str, Any] = {
        "t": round(timestamp),
        "lat": attributes.get("latitude"),
        "lon": attributes.get("longitude"),
    }
    accuracy = attributes.get("gps_accuracy")
    if accuracy is not None:
        raw_point["accuracy"] = accuracy
    try:
        return normalize_route_points([raw_point])[0]
    except ValueError:
        return None


async def _async_load_route_points(
    hass: HomeAssistant,
) -> dict[int, dict[str, Any]]:
    """Load retained route points once per Home Assistant start."""
    domain_data = hass.data[DOMAIN]
    cached = domain_data.get(ROUTE_HISTORY_CACHE)
    if isinstance(cached, dict):
        return cached

    try:
        payload = await domain_data[ROUTE_HISTORY_STORE].async_load()
    except (OSError, TypeError, ValueError) as err:
        _LOGGER.warning("Unable to load Renault route history: %s", err)
        payload = None

    raw_points = payload.get("points", []) if isinstance(payload, dict) else []
    records = raw_points.values() if isinstance(raw_points, dict) else raw_points
    try:
        normalized = normalize_route_points(records)
    except (TypeError, ValueError) as err:
        _LOGGER.warning("Ignoring invalid retained Renault route history: %s", err)
        normalized = []
    cached = {point["t"]: point for point in normalized}
    domain_data[ROUTE_HISTORY_CACHE] = cached
    return cached


async def _async_merge_route_points(
    hass: HomeAssistant,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge genuine GPS points without age-based deletion."""
    domain_data = hass.data[DOMAIN]
    lock = domain_data.setdefault(ROUTE_HISTORY_LOCK, asyncio.Lock())
    async with lock:
        cached = await _async_load_route_points(hass)
        changed = False
        for point in normalize_route_points(records):
            if cached.get(point["t"]) != point:
                cached[point["t"]] = point
                changed = True

        if changed:
            ordered = [cached[timestamp] for timestamp in sorted(cached)]
            await domain_data[ROUTE_HISTORY_STORE].async_save(
                {
                    "points": ordered,
                    "saved_at": datetime.now(UTC).isoformat(),
                }
            )
        return [cached[timestamp] for timestamp in sorted(cached)]


def _query_timestamp(request: web.Request, name: str) -> int | None:
    """Read an optional millisecond timestamp from a request query."""
    raw_value = request.query.get(name)
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError as err:
        raise ValueError(f"{name} must be a millisecond timestamp") from err
    if value < 0:
        raise ValueError(f"{name} must be a millisecond timestamp")
    return value


class ZoeNewRouteHistoryView(HomeAssistantView):
    """Read and import authenticated long-term GPS route history."""

    url = "/api/zoe_new_extended/route_history"
    name = "api:zoe_new_extended:route_history"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return retained points in the requested half-open time range."""
        hass: HomeAssistant = request.app["hass"]
        try:
            start = _query_timestamp(request, "start")
            end = _query_timestamp(request, "end")
            if start is not None and end is not None and end <= start:
                raise ValueError("end must be later than start")
        except ValueError as err:
            return self.json({"error": str(err)}, status_code=400)

        cached = await _async_load_route_points(hass)
        points = [
            cached[timestamp]
            for timestamp in sorted(cached)
            if (start is None or timestamp >= start)
            and (end is None or timestamp < end)
        ]
        return self.json({"points": points})

    async def post(self, request: web.Request) -> web.Response:
        """Merge genuine GPS points recovered from Recorder or a backup."""
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
            records = payload.get("points") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                raise ValueError("points must be a list")
            if len(records) > MAX_ROUTE_HISTORY_BATCH_POINTS:
                raise ValueError("too many route-history points")
            points = await _async_merge_route_points(hass, records)
        except (TypeError, ValueError) as err:
            return self.json({"error": str(err)}, status_code=400)
        except OSError as err:
            _LOGGER.warning("Unable to save Renault route history: %s", err)
            return self.json(
                {"error": "Route history could not be saved"},
                status_code=500,
            )
        return self.json({"points": len(points)})


def async_register_route_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Callable[[], None]:
    """Register the API and retain every future Renault location update."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(
        ROUTE_HISTORY_STORE,
        Store(
            hass,
            ROUTE_HISTORY_STORE_VERSION,
            f"{DOMAIN}.route_history_{entry.entry_id}",
        ),
    )
    if not domain_data.get(ROUTE_HISTORY_VIEW_REGISTERED):
        hass.http.register_view(ZoeNewRouteHistoryView())
        domain_data[ROUTE_HISTORY_VIEW_REGISTERED] = True

    async def async_location_changed(event: Event) -> None:
        point = _point_from_state(event.data.get("new_state"))
        if point is not None:
            await _async_merge_route_points(hass, [point])

    unsubscribe = async_track_state_change_event(
        hass,
        [ZOE_LOCATION_ENTITY_ID],
        async_location_changed,
    )
    current = _point_from_state(hass.states.get(ZOE_LOCATION_ENTITY_ID))
    if current is not None:
        hass.async_create_task(_async_merge_route_points(hass, [current]))
    return unsubscribe
