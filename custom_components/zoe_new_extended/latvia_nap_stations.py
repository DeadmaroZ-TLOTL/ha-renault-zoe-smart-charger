"""Latvia National Access Point EV infrastructure and live-status client."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .latvia_nap_data import current_download_url, parse_latvia_nap_catalog


STATUS_METADATA_URL = (
    "https://transportdata.gov.lv/en/api/v1/metadata/data/"
    "a377a160-baa1-4b67-b4e8-6612cd289e22"
)
INFRASTRUCTURE_METADATA_URL = (
    "https://transportdata.gov.lv/en/api/v1/metadata/data/"
    "d8e419c3-1585-4666-9067-85712befd2c4"
)
CACHE_SECONDS = 14 * 60
STATIC_CACHE_SECONDS = 6 * 60 * 60
MAX_XML_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT = ClientTimeout(total=75)
REQUEST_HEADERS = {
    "Accept": "application/json, application/xml;q=0.9",
    "Accept-Language": "en",
    "User-Agent": "HomeAssistant ZoeNewExtended/1.18",
}


class LatviaNapStationsClient:
    """Cache and normalize Latvia's official public DATEX II EV feeds."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._stations: list[dict[str, Any]] = []
        self._stations_by_id: dict[str, dict[str, Any]] = {}
        self._loaded_at = 0.0
        self._infrastructure_xml: bytes | None = None
        self._infrastructure_loaded_at = 0.0
        self._load_lock = asyncio.Lock()
        self.catalog_stats: dict[str, int] = {}

    async def async_catalog(self) -> list[dict[str, Any]]:
        """Return current public stations, prices, and connector status."""
        await self._async_ensure_catalog()
        return [dict(item) for item in self._stations]

    async def async_detail(self, station_id: str) -> dict[str, Any] | None:
        """Return the cached current detail for one NAP station."""
        await self._async_ensure_catalog()
        station = self._stations_by_id.get(str(station_id))
        return dict(station) if station is not None else None

    async def _async_ensure_catalog(self) -> None:
        if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
            return
        async with self._load_lock:
            if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
                return
            infrastructure_xml = await self._async_infrastructure_xml()
            status_xml = await self._async_download_current(STATUS_METADATA_URL)
            stations = await self.hass.async_add_executor_job(
                parse_latvia_nap_catalog,
                infrastructure_xml,
                status_xml,
            )
            self._stations = stations
            self._stations_by_id = {item["id"]: item for item in stations}
            self._loaded_at = monotonic()
            self.catalog_stats = {
                "normalized_station_count": len(stations),
                "infrastructure_bytes": len(infrastructure_xml),
                "status_bytes": len(status_xml),
            }

    async def _async_infrastructure_xml(self) -> bytes:
        if (
            self._infrastructure_xml is not None
            and monotonic() - self._infrastructure_loaded_at < STATIC_CACHE_SECONDS
        ):
            return self._infrastructure_xml
        payload = await self._async_download_current(INFRASTRUCTURE_METADATA_URL)
        self._infrastructure_xml = payload
        self._infrastructure_loaded_at = monotonic()
        return payload

    async def _async_download_current(self, metadata_url: str) -> bytes:
        session = async_get_clientsession(self.hass)
        async with session.get(
            metadata_url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            metadata = await response.json(content_type=None)
        if not isinstance(metadata, dict):
            raise ValueError("Latvia NAP returned invalid metadata")
        download_url = current_download_url(metadata)
        async with session.get(
            download_url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            if response.content_length and response.content_length > MAX_XML_BYTES:
                raise ValueError("Latvia NAP XML file is unexpectedly large")
            payload = await response.read()
        if not payload or len(payload) > MAX_XML_BYTES:
            raise ValueError("Latvia NAP XML file has an invalid size")
        return payload
