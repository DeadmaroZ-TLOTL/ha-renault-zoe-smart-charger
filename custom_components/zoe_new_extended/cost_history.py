"""Persist daily Renault driving costs for long-term monthly history."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .cost_history_data import normalize_cost_days

_LOGGER = logging.getLogger(__name__)

COST_HISTORY_STORE_VERSION = 1
COST_HISTORY_STORE = "_cost_history_store"
COST_HISTORY_CACHE = "_cost_history_cache"
COST_HISTORY_LOCK = "_cost_history_lock"
COST_HISTORY_VIEW_REGISTERED = "_cost_history_view_registered"
MAX_COST_HISTORY_DAYS = 5000


async def _async_load_cost_days(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Load the persisted daily records once per Home Assistant start."""
    domain_data = hass.data[DOMAIN]
    cached = domain_data.get(COST_HISTORY_CACHE)
    if isinstance(cached, dict):
        return cached

    try:
        payload = await domain_data[COST_HISTORY_STORE].async_load()
    except (OSError, TypeError, ValueError) as err:
        _LOGGER.warning("Unable to load Renault cost history: %s", err)
        payload = None

    raw_days = payload.get("days", {}) if isinstance(payload, dict) else {}
    records = raw_days.values() if isinstance(raw_days, dict) else []
    try:
        normalized = normalize_cost_days(records)
    except ValueError as err:
        _LOGGER.warning("Ignoring invalid persisted Renault cost history: %s", err)
        normalized = []
    cached = {record["day"]: record for record in normalized}
    domain_data[COST_HISTORY_CACHE] = cached
    return cached


async def _async_merge_cost_days(
    hass: HomeAssistant,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge fresh daily totals without discarding older retained months."""
    domain_data = hass.data[DOMAIN]
    lock = domain_data.setdefault(COST_HISTORY_LOCK, asyncio.Lock())
    async with lock:
        cached = await _async_load_cost_days(hass)
        for record in normalize_cost_days(records):
            cached[record["day"]] = record

        if len(cached) > MAX_COST_HISTORY_DAYS:
            retained_days = sorted(cached)[-MAX_COST_HISTORY_DAYS:]
            cached = {day: cached[day] for day in retained_days}
            domain_data[COST_HISTORY_CACHE] = cached

        await domain_data[COST_HISTORY_STORE].async_save(
            {
                "days": cached,
                "saved_at": datetime.now(UTC).isoformat(),
            }
        )
        return [cached[day] for day in sorted(cached)]


class ZoeNewCostHistoryView(HomeAssistantView):
    """Read and update the authenticated long-term daily cost history."""

    url = "/api/zoe_new_extended/cost_history"
    name = "api:zoe_new_extended:cost_history"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return every retained daily aggregate."""
        hass: HomeAssistant = request.app["hass"]
        days = await _async_load_cost_days(hass)
        return self.json({"days": [days[day] for day in sorted(days)]})

    async def post(self, request: web.Request) -> web.Response:
        """Merge daily aggregates calculated from Recorder trip history."""
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
            records = payload.get("days") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                raise ValueError("days must be a list")
            if len(records) > MAX_COST_HISTORY_DAYS:
                raise ValueError("too many daily records")
            days = await _async_merge_cost_days(hass, records)
        except (TypeError, ValueError) as err:
            return self.json({"error": str(err)}, status_code=400)
        except OSError as err:
            _LOGGER.warning("Unable to save Renault cost history: %s", err)
            return self.json(
                {"error": "Cost history could not be saved"},
                status_code=500,
            )
        return self.json({"days": days})


def async_register_cost_history_view(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Register the cost-history API and bind its persistent store."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(
        COST_HISTORY_STORE,
        Store(
            hass,
            COST_HISTORY_STORE_VERSION,
            f"{DOMAIN}.cost_history_{entry.entry_id}",
        ),
    )
    if domain_data.get(COST_HISTORY_VIEW_REGISTERED):
        return
    hass.http.register_view(ZoeNewCostHistoryView())
    domain_data[COST_HISTORY_VIEW_REGISTERED] = True
