"""Fetch charging transactions from multiple Mobilly and Elektrum accounts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
import logging
from typing import Any

from aiohttp import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    CookieJar,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .charging_accounts_data import (
    merge_account_transactions,
    parse_elektrum_transactions,
    tag_account_transactions,
)
from .const import (
    ACCOUNT_TYPE_ELEKTRUM_DRIVE,
    ACCOUNT_TYPE_MOBILLY,
    CONF_ACCOUNT_ENABLED,
    CONF_ACCOUNT_ID,
    CONF_ACCOUNT_NAME,
    CONF_ACCOUNT_TYPE,
    CONF_CHARGING_ACCOUNTS,
    CONF_ELEKTRUM_ACCESS_TOKEN,
    CONF_ELEKTRUM_DEVICE_UUID,
    CONF_MOBILLY_PASSWORD,
    CONF_MOBILLY_USERNAME,
)
from .mobilly_data import merge_transactions, parse_transactions_page

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=30)
HISTORY_DAYS = 400
REQUEST_TIMEOUT = ClientTimeout(total=35)
MOBILLY_BASE_URL = "https://mans.mobilly.lv"
MOBILLY_LOGIN_URL = f"{MOBILLY_BASE_URL}/lv/login"
MOBILLY_LOGIN_CHECK_URL = f"{MOBILLY_BASE_URL}/lv/login-check"
MOBILLY_PAYMENTS_URL = f"{MOBILLY_BASE_URL}/lv/my/statement/payments"
MOBILLY_MOBILE_URL = f"{MOBILLY_BASE_URL}/lv/my/statement/payments-mobile"
ELEKTRUM_API_URL = "https://eup.elektrum.lv/api/v3"
REQUEST_HEADERS = {
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "User-Agent": "HomeAssistant ZoeNewExtended/1.13",
}
ELEKTRUM_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Elektrum/2.7.1 (Language: lv; OS: Android)",
}


class ChargingAccountsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Collect exact charge transactions from every configured account."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Renault Zoe New charging accounts",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self._last_transactions_by_account: dict[
            str, list[dict[str, Any]]
        ] = {}

    @property
    def accounts(self) -> list[dict[str, Any]]:
        """Return a copy of all configured account records."""
        raw_accounts = self.entry.data.get(CONF_CHARGING_ACCOUNTS, [])
        if not isinstance(raw_accounts, list):
            return []
        return [dict(account) for account in raw_accounts if isinstance(account, dict)]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch enabled accounts independently so one failure cannot block others."""
        fetched_at = datetime.now(UTC).isoformat()
        accounts = self.accounts
        enabled = [
            account
            for account in accounts
            if account.get(CONF_ACCOUNT_ENABLED, True)
        ]
        results = await asyncio.gather(
            *(self._async_fetch_account(account) for account in enabled),
            return_exceptions=True,
        )

        account_status: list[dict[str, Any]] = []
        transaction_groups: list[list[dict[str, Any]]] = []
        for account, result in zip(enabled, results, strict=True):
            summary = self._account_summary(account)
            if isinstance(result, Exception):
                account_id = str(account.get(CONF_ACCOUNT_ID) or "")
                stale_transactions = self._last_transactions_by_account.get(
                    account_id, []
                )
                if stale_transactions:
                    transaction_groups.append(stale_transactions)
                summary.update(
                    {
                        "status": "stale" if stale_transactions else "error",
                        "error": _safe_error(result),
                        "transaction_count": len(stale_transactions),
                    }
                )
                _LOGGER.warning(
                    "Unable to refresh %s charging account %s: %s",
                    account.get(CONF_ACCOUNT_TYPE),
                    account.get(CONF_ACCOUNT_ID),
                    _safe_error(result),
                )
            else:
                transactions = result.get("transactions", [])
                transaction_groups.append(transactions)
                self._last_transactions_by_account[
                    str(account.get(CONF_ACCOUNT_ID) or "")
                ] = transactions
                summary.update(
                    {
                        "status": "ok",
                        "error": None,
                        "transaction_count": len(transactions),
                        "source_counts": result.get("source_counts", {}),
                    }
                )
            summary["last_refresh"] = fetched_at
            account_status.append(summary)

        disabled_ids = {
            account.get(CONF_ACCOUNT_ID)
            for account in enabled
        }
        account_status.extend(
            {
                **self._account_summary(account),
                "status": "disabled",
                "error": None,
                "transaction_count": 0,
                "last_refresh": fetched_at,
            }
            for account in accounts
            if account.get(CONF_ACCOUNT_ID) not in disabled_ids
        )
        transactions = merge_account_transactions(*transaction_groups)
        return {
            "configured": bool(accounts),
            "account_count": len(accounts),
            "enabled_account_count": len(enabled),
            "accounts": account_status,
            "transactions": transactions,
            "transaction_count": len(transactions),
            "fetched_at": fetched_at,
        }

    async def _async_fetch_account(
        self, account: dict[str, Any]
    ) -> dict[str, Any]:
        account_type = account.get(CONF_ACCOUNT_TYPE)
        if account_type == ACCOUNT_TYPE_MOBILLY:
            return await self._async_fetch_mobilly(account)
        if account_type == ACCOUNT_TYPE_ELEKTRUM_DRIVE:
            return await self._async_fetch_elektrum(account)
        raise ValueError("Unsupported charging account type")

    async def _async_fetch_mobilly(
        self, account: dict[str, Any]
    ) -> dict[str, Any]:
        username = str(account.get(CONF_MOBILLY_USERNAME) or "").strip()
        password = str(account.get(CONF_MOBILLY_PASSWORD) or "")
        if not username or not password:
            raise ValueError("Mobilly credentials are incomplete")

        session = ClientSession(
            cookie_jar=CookieJar(),
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        try:
            async with session.get(MOBILLY_LOGIN_URL) as response:
                response.raise_for_status()
                login_page = await response.text()
            login_data = {
                "_username": username,
                "_password": password,
            }
            login_token = _form_value(login_page, "_csrf_token")
            if login_token:
                login_data["_csrf_token"] = login_token
            async with session.post(
                MOBILLY_LOGIN_CHECK_URL,
                data=login_data,
                allow_redirects=True,
            ) as response:
                response.raise_for_status()
                if "/login" in str(response.url):
                    raise PermissionError("Mobilly authentication failed")
                await response.read()

            date_to = datetime.now().date()
            date_from = date_to - timedelta(days=HISTORY_DAYS)
            # Both Mobilly statement forms validate the same ISO date format.
            date_from_text = date_from.isoformat()
            date_to_text = date_to.isoformat()

            async with session.get(MOBILLY_PAYMENTS_URL) as response:
                response.raise_for_status()
                direct_form = await response.text()
            direct_params = {
                "payments[date_from]": date_from_text,
                "payments[date_to]": date_to_text,
                "payments[car]": "",
                "payments[service_provider]": "",
                "payments[service_group]": "21;ev_charging",
                "payments[properties]": "",
                "payments[submit]": "",
            }
            direct_token = _form_value(direct_form, "payments[_token]")
            if direct_token:
                direct_params["payments[_token]"] = direct_token
            async with session.get(
                MOBILLY_PAYMENTS_URL, params=direct_params
            ) as response:
                response.raise_for_status()
                direct_page = await response.text()

            async with session.get(MOBILLY_MOBILE_URL) as response:
                response.raise_for_status()
                mobile_form = await response.text()
            mobile_data = {
                "form[date_from]": date_from_text,
                "form[date_to]": date_to_text,
                "form[submit]": "",
            }
            mobile_token = _form_value(mobile_form, "form[_token]")
            if mobile_token:
                mobile_data["form[_token]"] = mobile_token
            async with session.post(
                MOBILLY_MOBILE_URL, data=mobile_data
            ) as response:
                response.raise_for_status()
                mobile_page = await response.text()
        finally:
            await session.close()

        direct = parse_transactions_page(direct_page, source_page="payments")
        mobile = parse_transactions_page(
            mobile_page, source_page="payments_mobile"
        )
        transactions = merge_transactions(direct, mobile)
        transactions = tag_account_transactions(
            transactions,
            account_id=str(account[CONF_ACCOUNT_ID]),
            account_name=str(account.get(CONF_ACCOUNT_NAME) or "Mobilly"),
            account_type=ACCOUNT_TYPE_MOBILLY,
        )
        return {
            "transactions": transactions,
            "source_counts": {
                "payments": len(direct),
                "payments_mobile": len(mobile),
            },
        }

    async def _async_fetch_elektrum(
        self, account: dict[str, Any]
    ) -> dict[str, Any]:
        token = str(account.get(CONF_ELEKTRUM_ACCESS_TOKEN) or "")
        if not token:
            raise PermissionError("Elektrum Drive account needs authentication")

        payload, status = await self._async_elektrum_request(
            "transactions", token
        )
        if status == 401:
            refresh_payload, refresh_status = await self._async_elektrum_request(
                "auth/refresh", token
            )
            if refresh_status >= 400:
                raise PermissionError("Elektrum Drive session has expired")
            refreshed_token = _access_token(refresh_payload)
            if not refreshed_token:
                raise PermissionError("Elektrum Drive did not return a new token")
            token = refreshed_token
            self._store_refreshed_token(
                str(account[CONF_ACCOUNT_ID]),
                token,
                str(account.get(CONF_ELEKTRUM_DEVICE_UUID) or ""),
            )
            payload, status = await self._async_elektrum_request(
                "transactions", token
            )
        if status >= 400:
            raise PermissionError(f"Elektrum Drive request failed ({status})")

        transactions = parse_elektrum_transactions(
            payload,
            account_id=str(account[CONF_ACCOUNT_ID]),
            account_name=str(
                account.get(CONF_ACCOUNT_NAME) or "Elektrum Drive"
            ),
        )
        return {
            "transactions": transactions,
            "source_counts": {"elektrum_drive_app": len(transactions)},
        }

    async def _async_elektrum_request(
        self, path: str, token: str
    ) -> tuple[dict[str, Any], int]:
        headers = {**ELEKTRUM_HEADERS, "Authorization": f"Bearer {token}"}
        async with ClientSession(
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        ) as session:
            async with session.get(f"{ELEKTRUM_API_URL}/{path}") as response:
                status = response.status
                try:
                    payload = await response.json(content_type=None)
                except (TypeError, ValueError):
                    payload = {}
        return payload if isinstance(payload, dict) else {}, status

    def _store_refreshed_token(
        self, account_id: str, token: str, device_uuid: str
    ) -> None:
        accounts = self.accounts
        changed = False
        for account in accounts:
            if str(account.get(CONF_ACCOUNT_ID)) != account_id:
                continue
            account[CONF_ELEKTRUM_ACCESS_TOKEN] = token
            if device_uuid:
                account[CONF_ELEKTRUM_DEVICE_UUID] = device_uuid
            changed = True
            break
        if not changed:
            return
        data = dict(self.entry.data)
        data[CONF_CHARGING_ACCOUNTS] = accounts
        self.hass.config_entries.async_update_entry(self.entry, data=data)

    @staticmethod
    def _account_summary(account: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": account.get(CONF_ACCOUNT_ID),
            "name": account.get(CONF_ACCOUNT_NAME),
            "type": account.get(CONF_ACCOUNT_TYPE),
            "enabled": bool(account.get(CONF_ACCOUNT_ENABLED, True)),
        }


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        name = values.get("name")
        if name:
            self.values[name] = values.get("value") or ""


def _form_value(page: str, name: str) -> str | None:
    parser = _InputParser()
    parser.feed(page)
    return parser.values.get(name)


def _access_token(payload: dict[str, Any]) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    value = data.get("accessToken")
    return str(value) if value else None


def _safe_error(error: Exception) -> str:
    if isinstance(error, ClientResponseError):
        return f"HTTP {error.status}"
    if isinstance(error, (ClientError, TimeoutError)):
        return type(error).__name__
    return str(error)[:160] or type(error).__name__
