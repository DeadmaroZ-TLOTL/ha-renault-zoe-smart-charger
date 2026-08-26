"""Persist complete Renault trip and road-surface results."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .trip_history_data import normalize_trip_records


_LOGGER = logging.getLogger(__name__)

TRIP_HISTORY_STORE_VERSION = 1
TRIP_HISTORY_STORE = "_trip_history_store"
TRIP_HISTORY_CACHE = "_trip_history_cache"
TRIP_HISTORY_LOCK = "_trip_history_lock"
TRIP_HISTORY_VIEW_REGISTERED = "_trip_history_view_registered"
MAX_TRIP_HISTORY_BATCH_RECORDS = 10_000


async def _async_load_trip_records(
    hass: HomeAssistant,
) -> dict[str, dict[str, Any]]:
    """Load the persisted trip report once per Home Assistant start."""
    domain_data = hass.data[DOMAIN]
    cached = domain_data.get(TRIP_HISTORY_CACHE)
    if isinstance(cached, dict):
        return cached

    try:
        payload = await domain_data[TRIP_HISTORY_STORE].async_load()
    except (OSError, TypeError, ValueError) as err:
        _LOGGER.warning("Unable to load Renault trip history: %s", err)
        payload = None

    raw_records = payload.get("trips", []) if isinstance(payload, dict) else []
    records = raw_records.values() if isinstance(raw_records, dict) else raw_records
    try:
        normalized = normalize_trip_records(records)
    except (TypeError, ValueError) as err:
        _LOGGER.warning("Ignoring invalid retained Renault trip history: %s", err)
        normalized = []
    cached = {record["id"]: record for record in normalized}
    domain_data[TRIP_HISTORY_CACHE] = cached
    return cached


async def _async_merge_trip_records(
    hass: HomeAssistant,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge classified trips without deleting older results."""
    domain_data = hass.data[DOMAIN]
    lock = domain_data.setdefault(TRIP_HISTORY_LOCK, asyncio.Lock())
    async with lock:
        cached = await _async_load_trip_records(hass)
        for record in normalize_trip_records(records):
            cached[record["id"]] = record
        ordered = sorted(
            cached.values(),
            key=lambda record: (record["start"], record["id"]),
        )
        await domain_data[TRIP_HISTORY_STORE].async_save(
            {
                "trips": ordered,
                "saved_at": datetime.now(UTC).isoformat(),
            }
        )
        return ordered


def _query_timestamp(request: web.Request, name: str) -> int | None:
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


class ZoeNewTripHistoryView(HomeAssistantView):
    """Read and update the authenticated long-term trip report."""

    url = "/api/zoe_new_extended/trip_history"
    name = "api:zoe_new_extended:trip_history"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return retained trips intersecting the requested period."""
        hass: HomeAssistant = request.app["hass"]
        try:
            start = _query_timestamp(request, "start")
            end = _query_timestamp(request, "end")
            if start is not None and end is not None and end <= start:
                raise ValueError("end must be later than start")
        except ValueError as err:
            return self.json({"error": str(err)}, status_code=400)

        cached = await _async_load_trip_records(hass)
        records = [
            record
            for record in sorted(
                cached.values(),
                key=lambda item: (item["start"], item["id"]),
            )
            if (start is None or record["end"] >= start)
            and (end is None or record["start"] < end)
        ]
        return self.json({"trips": records})

    async def post(self, request: web.Request) -> web.Response:
        """Merge road-surface results calculated from genuine GPS routes."""
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
            records = payload.get("trips") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                raise ValueError("trips must be a list")
            if len(records) > MAX_TRIP_HISTORY_BATCH_RECORDS:
                raise ValueError("too many trip-history records")
            trips = await _async_merge_trip_records(hass, records)
        except (TypeError, ValueError) as err:
            return self.json({"error": str(err)}, status_code=400)
        except OSError as err:
            _LOGGER.warning("Unable to save Renault trip history: %s", err)
            return self.json(
                {"error": "Trip history could not be saved"},
                status_code=500,
            )
        return self.json({"trips": len(trips)})


def async_register_trip_history_view(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Register the trip-history API and persistent store."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(
        TRIP_HISTORY_STORE,
        Store(
            hass,
            TRIP_HISTORY_STORE_VERSION,
            f"{DOMAIN}.trip_history_{entry.entry_id}",
        ),
    )
    if domain_data.get(TRIP_HISTORY_VIEW_REGISTERED):
        return
    hass.http.register_view(ZoeNewTripHistoryView())
    domain_data[TRIP_HISTORY_VIEW_REGISTERED] = True
