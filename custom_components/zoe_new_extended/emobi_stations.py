"""Official e-mobi charging-station catalog and live status client."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .stations_data import normalize_emobi_station

EMOBI_STATIONS_URL = "https://e-mobi.lv/api/stations"
CACHE_SECONDS = 30
REQUEST_TIMEOUT = ClientTimeout(total=35)
REQUEST_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "lv",
    "User-Agent": "HomeAssistant ZoeNewExtended/1.18",
}


class EmobiStationsClient:
    """Cache and normalize the official e-mobi public live catalog."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._stations: list[dict[str, Any]] = []
        self._stations_by_id: dict[str, dict[str, Any]] = {}
        self._loaded_at = 0.0
        self._load_lock = asyncio.Lock()
        self.catalog_stats: dict[str, int] = {}

    async def async_catalog(self) -> list[dict[str, Any]]:
        """Return the current official e-mobi stations."""
        await self._async_ensure_catalog()
        return [dict(item) for item in self._stations]

    async def async_detail(self, station_id: str) -> dict[str, Any] | None:
        """Return current connector price and status for one station."""
        await self._async_ensure_catalog()
        station = self._stations_by_id.get(str(station_id))
        return dict(station) if station is not None else None

    async def _async_ensure_catalog(self) -> None:
        if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
            return
        async with self._load_lock:
            if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
                return
            session = async_get_clientsession(self.hass)
            async with session.get(
                EMOBI_STATIONS_URL,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
            features = payload.get("features") if isinstance(payload, dict) else None
            if not isinstance(features, list):
                raise ValueError("e-mobi response does not contain a feature list")
            stations = [
                normalized
                for feature in features
                if isinstance(feature, dict)
                if (normalized := normalize_emobi_station(feature)) is not None
            ]
            self._stations = stations
            self._stations_by_id = {item["id"]: item for item in stations}
            self._loaded_at = monotonic()
            self.catalog_stats = {
                "raw_feature_count": len(features),
                "normalized_station_count": len(stations),
                "rejected_feature_count": len(features) - len(stations),
            }
