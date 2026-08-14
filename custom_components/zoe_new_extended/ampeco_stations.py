"""Public Ignitis ON and IKRAUTAS AMPECO station clients."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .ampeco_auth import (
    IGNITIS_ON,
    IKRAUTAS,
    AmpecoProviderConfig,
    ampeco_app_headers,
)
from .ampeco_stations_data import normalize_ampeco_catalog
from .charging_accounts_data import deduplicate_account_records
from .const import (
    CONF_ACCOUNT_ENABLED,
    CONF_ACCOUNT_TYPE,
    CONF_AMPECO_ACCESS_TOKEN,
    CONF_CHARGING_ACCOUNTS,
)


CACHE_SECONDS = 2 * 60
DETAIL_BATCH_SIZE = 100
REQUEST_TIMEOUT = ClientTimeout(total=75)


class AmpecoStationsClient:
    """Read a complete AMPECO public app station catalog."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config: AmpecoProviderConfig,
        entry: ConfigEntry | None = None,
    ) -> None:
        self.hass = hass
        self.config = config
        self.entry = entry
        self.provider = config.provider
        self.provider_group = config.provider_group
        self.operator = config.display_name
        self.host = config.host
        self.operator_country = config.operator_country
        self._stations: list[dict[str, Any]] = []
        self._stations_by_id: dict[str, dict[str, Any]] = {}
        self._loaded_at = 0.0
        self._load_lock = asyncio.Lock()
        self._authenticated_catalog = False
        self.catalog_stats: dict[str, int] = {}

    async def async_catalog(self) -> list[dict[str, Any]]:
        """Return all public locations with connector tariffs and status."""
        await self._async_ensure_catalog()
        return [dict(item) for item in self._stations]

    async def async_detail(self, station_id: str) -> dict[str, Any] | None:
        """Return current cached connector detail for one location."""
        await self._async_ensure_catalog()
        station = self._stations_by_id.get(str(station_id))
        return dict(station) if station is not None else None

    async def _async_ensure_catalog(self) -> None:
        if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
            return
        async with self._load_lock:
            if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
                return
            self._authenticated_catalog = False
            pins = await self._async_pins()
            location_ids = sorted(
                {
                    str(location_id)
                    for pin in pins
                    for location_id in _location_ids(pin)
                    if location_id is not None
                }
            )
            batches = [
                location_ids[index : index + DETAIL_BATCH_SIZE]
                for index in range(0, len(location_ids), DETAIL_BATCH_SIZE)
            ]
            results = await asyncio.gather(
                *(self._async_locations(batch) for batch in batches)
            )
            stations: list[dict[str, Any]] = []
            returned_location_ids: set[str] = set()
            for payload in results:
                locations = payload.get("locations")
                tariffs = payload.get("tariffs")
                locations = locations if isinstance(locations, list) else []
                tariffs = tariffs if isinstance(tariffs, list) else []
                returned_location_ids.update(
                    str(item.get("id"))
                    for item in locations
                    if isinstance(item, dict) and item.get("id") is not None
                )
                stations.extend(
                    normalize_ampeco_catalog(
                        locations,
                        tariffs,
                        provider=self.provider,
                        provider_group=self.provider_group,
                        operator=self.operator,
                    )
                )
            self._stations = stations
            self._stations_by_id = {item["id"]: item for item in stations}
            self._loaded_at = monotonic()
            self.catalog_stats = {
                "pin_count": len(pins),
                "requested_location_count": len(location_ids),
                "returned_location_count": len(returned_location_ids),
                "normalized_station_count": len(stations),
                "authenticated": int(self._authenticated_catalog),
            }

    async def _async_pins(self) -> list[dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        params = {
            "minLatitude": "-90",
            "maxLatitude": "90",
            "minLongitude": "-180",
            "maxLongitude": "180",
            "limit": "5000",
            "withCurrentTypes": "true",
            "includeAvailability": "true",
            "operatorCountry": self.operator_country,
        }
        payload = None
        token = self._access_token()
        for access_token in ((token, None) if token else (None,)):
            async with session.get(
                f"https://{self.host}/api/v1/app/pins",
                params=params,
                headers=self._headers(access_token),
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status in {401, 403} and access_token:
                    continue
                response.raise_for_status()
                payload = await response.json(content_type=None)
                self._authenticated_catalog |= bool(access_token)
                break
        pins = payload.get("pins") if isinstance(payload, dict) else None
        if not isinstance(pins, list):
            raise ValueError(f"{self.operator} response does not contain pins")
        return [item for item in pins if isinstance(item, dict)]

    async def _async_locations(self, location_ids: list[str]) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        payload = None
        token = self._access_token()
        for access_token in ((token, None) if token else (None,)):
            async with session.post(
                f"https://{self.host}/api/v1/app/locations",
                params={"operatorCountry": self.operator_country},
                headers=self._headers(access_token),
                json={
                    "locations": {
                        location_id: "" for location_id in location_ids
                    }
                },
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status in {401, 403} and access_token:
                    continue
                response.raise_for_status()
                payload = await response.json(content_type=None)
                self._authenticated_catalog |= bool(access_token)
                break
        if not isinstance(payload, dict):
            raise ValueError(f"{self.operator} returned invalid location detail")
        return payload

    def _headers(self, access_token: str | None = None) -> dict[str, str]:
        return ampeco_app_headers(self.config, access_token)

    def _access_token(self) -> str | None:
        if self.entry is None:
            return None
        raw_accounts = self.entry.data.get(CONF_CHARGING_ACCOUNTS, [])
        if not isinstance(raw_accounts, list):
            return None
        for account in deduplicate_account_records(
            item for item in raw_accounts if isinstance(item, dict)
        ):
            if account.get(CONF_ACCOUNT_TYPE) != self.config.account_type:
                continue
            if not account.get(CONF_ACCOUNT_ENABLED, True):
                continue
            token = str(account.get(CONF_AMPECO_ACCESS_TOKEN) or "").strip()
            if token:
                return token
        return None


def _location_ids(pin: dict[str, Any]) -> list[Any]:
    values = pin.get("underlyingLocationIds")
    if isinstance(values, list) and values:
        return values
    return [pin.get("id")]


def ignitis_on_client(
    hass: HomeAssistant,
    entry: ConfigEntry | None = None,
) -> AmpecoStationsClient:
    """Build the official Ignitis ON public catalog client."""
    return _provider_client(hass, IGNITIS_ON, entry)


def ikrautas_client(
    hass: HomeAssistant,
    entry: ConfigEntry | None = None,
) -> AmpecoStationsClient:
    """Build the official IKRAUTAS public catalog client."""
    return _provider_client(hass, IKRAUTAS, entry)


def _provider_client(
    hass: HomeAssistant,
    config: AmpecoProviderConfig,
    entry: ConfigEntry | None = None,
) -> AmpecoStationsClient:
    return AmpecoStationsClient(
        hass,
        config=config,
        entry=entry,
    )
