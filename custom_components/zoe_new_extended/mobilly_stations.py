"""Mobilly EV charging catalog and authenticated live station client."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ACCOUNT_TYPE_MOBILLY,
    CONF_ACCOUNT_ENABLED,
    CONF_ACCOUNT_ID,
    CONF_ACCOUNT_TYPE,
    CONF_CHARGING_ACCOUNTS,
    CONF_MOBILLY_ACCESS_TOKEN,
    CONF_MOBILLY_PHONE,
    CONF_MOBILLY_REFRESH_TOKEN,
)
from .mobilly_auth import (
    MOBILLY_API_URL,
    MOBILLY_AUTH_URL,
    mobilly_access_token,
    mobilly_app_headers,
    mobilly_refresh_token,
    mobilly_token_credentials,
)
from .stations_data import (
    merge_mobilly_station_detail,
    merge_mobilly_statuses,
    normalize_mobilly_station,
)

MOBILLY_SITES_URL = "https://api.mobilly.lv/v3/app/sites"
MOBILLY_SITE_TYPES = "car_wash,ev_charge,parking"
CACHE_SECONDS = 6 * 60 * 60
LIVE_CACHE_SECONDS = 30
REQUEST_TIMEOUT = ClientTimeout(total=35)
REQUEST_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "lv",
    "User-Agent": "HomeAssistant ZoeNewExtended/1.15",
}


class MobillyStationsClient:
    """Cache and normalize Mobilly's public EV station catalog."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._stations: list[dict[str, Any]] = []
        self._stations_by_id: dict[str, dict[str, Any]] = {}
        self._loaded_at = 0.0
        self._live_loaded_at = 0.0
        self._load_lock = asyncio.Lock()

    async def async_catalog(self) -> list[dict[str, Any]]:
        """Return public stations enriched with authenticated live status."""
        await self._async_ensure_catalog()
        if not self._app_accounts():
            return [dict(item) for item in self._stations]
        if monotonic() - self._live_loaded_at >= LIVE_CACHE_SECONDS:
            try:
                payload = await self._async_app_get(
                    "ev-charge/sites-status",
                    params={"ids": ""},
                )
            except (RuntimeError, TimeoutError, ValueError):
                return [dict(item) for item in self._stations]
            self._stations = merge_mobilly_statuses(self._stations, payload)
            self._stations_by_id = {item["id"]: item for item in self._stations}
            self._live_loaded_at = monotonic()
        return [dict(item) for item in self._stations]

    async def async_detail(self, station_id: str) -> dict[str, Any] | None:
        """Return protected connector price/status when an app token exists."""
        await self._async_ensure_catalog()
        station = self._stations_by_id.get(str(station_id))
        if station is None:
            return None
        if self._app_accounts():
            payload = await self._async_app_get(f"ev-charge/site/{station_id}")
            return merge_mobilly_station_detail(station, payload)
        return {
            **station,
            "detail_source": "mobilly_public_catalog",
            "live_data_available": False,
            "live_data_message": "Link the Mobilly app account for live data",
        }

    def _app_accounts(self) -> list[dict[str, Any]]:
        accounts = self.entry.data.get(CONF_CHARGING_ACCOUNTS, [])
        if not isinstance(accounts, list):
            return []
        return [
                dict(account)
                for account in accounts
                if isinstance(account, dict)
                and account.get(CONF_ACCOUNT_TYPE) == ACCOUNT_TYPE_MOBILLY
                and account.get(CONF_ACCOUNT_ENABLED, True)
                and account.get(CONF_MOBILLY_ACCESS_TOKEN)
        ]

    async def _async_app_get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        accounts = self._app_accounts()
        if not accounts:
            raise RuntimeError("Mobilly app account is not linked")
        last_error: RuntimeError | None = None
        for account in accounts:
            try:
                return await self._async_app_get_for_account(
                    account,
                    path,
                    params=params,
                )
            except RuntimeError as err:
                last_error = err
        raise last_error or RuntimeError("No Mobilly app account is available")

    async def _async_app_get_for_account(
        self,
        account: dict[str, Any],
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        token = str(account.get(CONF_MOBILLY_ACCESS_TOKEN) or "")
        payload, status = await self._async_request(
            f"{MOBILLY_API_URL}/{path}",
            headers=mobilly_app_headers(token),
            params=params,
        )
        if status == 401:
            token = await self._async_refresh_token(account)
            payload, status = await self._async_request(
                f"{MOBILLY_API_URL}/{path}",
                headers=mobilly_app_headers(token),
                params=params,
            )
        if status >= 400:
            raise RuntimeError(f"Mobilly app request failed ({status})")
        return payload

    async def _async_refresh_token(self, account: dict[str, Any]) -> str:
        refresh_token = str(account.get(CONF_MOBILLY_REFRESH_TOKEN) or "")
        phone = str(account.get(CONF_MOBILLY_PHONE) or "")
        if not refresh_token or not phone:
            raise RuntimeError("Mobilly app session has expired")
        payload, status = await self._async_request(
            f"{MOBILLY_AUTH_URL}/token/refresh_token",
            method="POST",
            headers=mobilly_app_headers(),
            json_body=mobilly_token_credentials(
                phone,
                refresh_token,
                grant_type="refresh_token",
            )["tokenCredentials"],
        )
        access_token = mobilly_access_token(payload)
        if status >= 400 or not access_token:
            raise RuntimeError("Mobilly app session refresh failed")
        new_refresh = mobilly_refresh_token(payload) or refresh_token
        self._store_tokens(
            str(account.get(CONF_ACCOUNT_ID) or ""),
            access_token,
            new_refresh,
        )
        return access_token

    async def _async_request(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str],
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        session = async_get_clientsession(self.hass)
        async with session.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            try:
                payload = await response.json(content_type=None)
            except (TypeError, ValueError):
                payload = {}
            return payload if isinstance(payload, dict) else {}, response.status

    def _store_tokens(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
    ) -> None:
        accounts = self.entry.data.get(CONF_CHARGING_ACCOUNTS, [])
        if not isinstance(accounts, list):
            return
        updated_accounts = []
        changed = False
        for source in accounts:
            account = dict(source) if isinstance(source, dict) else source
            if isinstance(account, dict) and str(account.get(CONF_ACCOUNT_ID)) == account_id:
                account[CONF_MOBILLY_ACCESS_TOKEN] = access_token
                account[CONF_MOBILLY_REFRESH_TOKEN] = refresh_token
                changed = True
            updated_accounts.append(account)
        if changed:
            data = dict(self.entry.data)
            data[CONF_CHARGING_ACCOUNTS] = updated_accounts
            self.hass.config_entries.async_update_entry(self.entry, data=data)

    async def _async_ensure_catalog(self) -> None:
        if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
            return
        async with self._load_lock:
            if self._stations and monotonic() - self._loaded_at < CACHE_SECONDS:
                return
            session = async_get_clientsession(self.hass)
            async with session.get(
                MOBILLY_SITES_URL,
                params={
                    "type": MOBILLY_SITE_TYPES,
                    "excludeRsLocationPolygons": "true",
                    "lang": "lv",
                },
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
            raw_sites = (
                payload.get("sites") if isinstance(payload, dict) else None
            )
            if not isinstance(raw_sites, list):
                raise ValueError(
                    "Mobilly station response does not contain a site list"
                )
            stations = [
                normalized
                for site in raw_sites
                if isinstance(site, dict)
                if (normalized := normalize_mobilly_station(site)) is not None
            ]
            self._stations = stations
            self._stations_by_id = {item["id"]: item for item in stations}
            self._loaded_at = monotonic()
