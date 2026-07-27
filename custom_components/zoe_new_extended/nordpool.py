"""Selected Nord Pool area price for the Zoe smart charger."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NORDPOOL_AREA,
    DEFAULT_NORDPOOL_AREA,
    NORDPOOL_AREAS,
)

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(minutes=15)
DYNAMIC_PRICE_ENTITY_ID = "sensor.renault_zoe_new_nord_pool_price"


class NordPoolPriceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Provide a stable price sensor for the selected Nord Pool area."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the selected-area coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Renault Zoe New Nord Pool price",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry

    @property
    def selected_area(self) -> str:
        """Return the configured area, falling back to Latvia."""
        area = self.entry.options.get(CONF_NORDPOOL_AREA, DEFAULT_NORDPOOL_AREA)
        return area if area in NORDPOOL_AREAS else DEFAULT_NORDPOOL_AREA

    async def _async_update_data(self) -> dict[str, Any]:
        """Load prices from an existing sensor or the Nord Pool action."""
        area = self.selected_area
        source = self._find_source_sensor(area)
        if source is not None:
            return self._data_from_sensor(source, area)

        today = dt_util.now().date()
        today_result, tomorrow_result = await asyncio.gather(
            self._async_fetch_day(today, area),
            self._async_fetch_day(today + timedelta(days=1), area),
            return_exceptions=True,
        )
        if isinstance(today_result, Exception):
            err = today_result
            _LOGGER.warning("Unable to load Nord Pool prices for %s: %s", area, err)
            return self._empty_data(area, str(err))
        raw_today = today_result
        if isinstance(tomorrow_result, Exception):
            _LOGGER.debug(
                "Nord Pool tomorrow prices are unavailable: %s", tomorrow_result
            )
            raw_tomorrow = []
        else:
            raw_tomorrow = tomorrow_result

        now = dt_util.now()
        current_price = next(
            (
                item["value"]
                for item in raw_today + raw_tomorrow
                if _contains_time(item, now)
            ),
            None,
        )
        values_today = [item["value"] for item in raw_today]
        values_tomorrow = [item["value"] for item in raw_tomorrow]
        country, vat = NORDPOOL_AREAS[area]
        return {
            "value": current_price,
            "average": (
                sum(values_today) / len(values_today) if values_today else None
            ),
            "min": min(values_today) if values_today else None,
            "max": max(values_today) if values_today else None,
            "today": values_today,
            "tomorrow": values_tomorrow,
            "tomorrow_valid": bool(raw_tomorrow),
            "raw_today": raw_today,
            "raw_tomorrow": raw_tomorrow,
            "currency": "EUR",
            "country": country,
            "region": area,
            "vat_percent": vat * 100,
            "price_in_cents": True,
            "source": "nordpool.hourly",
            "source_entity": None,
            "last_fetched": datetime.now(UTC).isoformat(),
        }

    def _find_source_sensor(self, area: str) -> State | None:
        """Find an installed Nord Pool sensor for the selected area."""
        for entity_id in self.hass.states.async_entity_ids("sensor"):
            if entity_id == DYNAMIC_PRICE_ENTITY_ID:
                continue
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            attributes = state.attributes
            if (
                attributes.get("region") == area
                and attributes.get("currency") == "EUR"
                and attributes.get("price_in_cents") is True
                and attributes.get("raw_today")
            ):
                return state
        return None

    def _data_from_sensor(self, state: State, area: str) -> dict[str, Any]:
        """Normalize an existing Nord Pool sensor without losing its history."""
        attributes = state.attributes
        value = _as_float(state.state)
        country, vat = NORDPOOL_AREAS[area]
        raw_today, raw_tomorrow = _normalize_source_slots(
            [
                *attributes.get("raw_today", []),
                *attributes.get("raw_tomorrow", []),
            ],
            dt_util.now().date(),
        )
        values_today = [item["value"] for item in raw_today]
        values_tomorrow = [item["value"] for item in raw_tomorrow]
        return {
            "value": value,
            "average": (
                sum(values_today) / len(values_today)
                if values_today
                else attributes.get("average")
            ),
            "min": min(values_today) if values_today else attributes.get("min"),
            "max": max(values_today) if values_today else attributes.get("max"),
            "today": values_today or attributes.get("today", []),
            "tomorrow": values_tomorrow or attributes.get("tomorrow", []),
            "tomorrow_valid": bool(raw_tomorrow),
            "raw_today": raw_today,
            "raw_tomorrow": raw_tomorrow,
            "currency": "EUR",
            "country": attributes.get("country", country),
            "region": area,
            "vat_percent": vat * 100,
            "price_in_cents": True,
            "source": "sensor",
            "source_entity": state.entity_id,
            "last_fetched": datetime.now(UTC).isoformat(),
        }

    async def _async_fetch_day(self, day: date, area: str) -> list[dict[str, Any]]:
        """Fetch and normalize one day of EUR/MWh Nord Pool entries."""
        if not self.hass.services.has_service("nordpool", "hourly"):
            raise RuntimeError("Nord Pool hourly action is unavailable")
        response = await self.hass.services.async_call(
            "nordpool",
            "hourly",
            {"currency": "EUR", "date": day.isoformat(), "area": area},
            blocking=True,
            return_response=True,
        )
        payload = response.get("service_response", response) if response else {}
        entries = payload.get("multiAreaEntries", [])
        _country, vat = NORDPOOL_AREAS[area]
        normalized = []
        for entry in entries:
            raw_value = entry.get("entryPerArea", {}).get(area)
            start = dt_util.parse_datetime(entry.get("deliveryStart", ""))
            end = dt_util.parse_datetime(entry.get("deliveryEnd", ""))
            if raw_value is None or start is None or end is None:
                continue
            normalized.append(
                {
                    "start": dt_util.as_local(start).isoformat(),
                    "end": dt_util.as_local(end).isoformat(),
                    "value": round(float(raw_value) * (1 + vat) / 10, 3),
                }
            )
        normalized.sort(key=lambda item: item["start"])
        if not normalized:
            raise RuntimeError(f"Nord Pool returned no {area} prices for {day}")
        return normalized

    @staticmethod
    def _empty_data(area: str, error: str) -> dict[str, Any]:
        """Return useful attributes while the price source is unavailable."""
        country, vat = NORDPOOL_AREAS[area]
        return {
            "value": None,
            "today": [],
            "tomorrow": [],
            "tomorrow_valid": False,
            "raw_today": [],
            "raw_tomorrow": [],
            "currency": "EUR",
            "country": country,
            "region": area,
            "vat_percent": vat * 100,
            "price_in_cents": True,
            "source": None,
            "source_entity": None,
            "error": error,
            "last_fetched": datetime.now(UTC).isoformat(),
        }


def _contains_time(item: dict[str, Any], now) -> bool:
    """Return whether a normalized interval contains now."""
    start = dt_util.parse_datetime(item["start"])
    end = dt_util.parse_datetime(item["end"])
    return start is not None and end is not None and start <= now < end


def _normalize_source_slots(
    slots: list[dict[str, Any]], today: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate source intervals and split them into today and tomorrow."""
    tomorrow = today + timedelta(days=1)
    by_day: dict[date, dict[str, dict[str, Any]]] = {
        today: {},
        tomorrow: {},
    }
    for item in slots:
        if not isinstance(item, dict):
            continue
        start = dt_util.parse_datetime(str(item.get("start", "")))
        end = dt_util.parse_datetime(str(item.get("end", "")))
        value = _as_float(item.get("value"))
        if start is None or end is None or value is None:
            continue
        local_start = dt_util.as_local(start)
        day_slots = by_day.get(local_start.date())
        if day_slots is None:
            continue
        local_end = dt_util.as_local(end)
        start_key = local_start.isoformat()
        day_slots[start_key] = {
            "start": start_key,
            "end": local_end.isoformat(),
            "value": value,
        }
    return (
        list(sorted(by_day[today].values(), key=lambda item: item["start"])),
        list(sorted(by_day[tomorrow].values(), key=lambda item: item["start"])),
    )


def _as_float(value: str) -> float | None:
    """Convert a state to float while preserving unavailable values."""
    if value in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
