"""Fetch exact transactions from all configured charging accounts."""

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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .ampeco_auth import (
    AMPECO_ACCOUNT_TYPES,
    ampeco_app_headers,
    ampeco_provider,
    ampeco_token_form,
    ampeco_token_values,
)
from .ampeco_history import ampeco_history_page, parse_ampeco_transactions
from .charging_accounts_data import (
    deduplicate_account_records,
    elektrum_month_keys,
    elektrum_profile_state,
    elektrum_token_can_replace,
    merge_account_transactions,
    parse_elektrum_transactions,
    tag_account_transactions,
)
from .const import (
    CONF_AMPECO_ACCESS_TOKEN,
    CONF_AMPECO_REFRESH_TOKEN,
    CONF_AMPECO_TOKEN_EXPIRES_AT,
    ACCOUNT_TYPE_ELEKTRUM_DRIVE,
    ACCOUNT_TYPE_MOBILLY,
    CONF_ACCOUNT_ENABLED,
    CONF_ACCOUNT_ID,
    CONF_ACCOUNT_NAME,
    CONF_ACCOUNT_TYPE,
    CONF_CHARGING_ACCOUNTS,
    CONF_ELEKTRUM_ACCESS_TOKEN,
    CONF_ELEKTRUM_AGREEMENT_ID,
    CONF_ELEKTRUM_DEVICE_UUID,
    CONF_MOBILLY_ACCESS_TOKEN,
    CONF_MOBILLY_PASSWORD,
    CONF_MOBILLY_PHONE,
    CONF_MOBILLY_REFRESH_TOKEN,
    CONF_MOBILLY_USERNAME,
    DOMAIN,
)
from .elektrum_login import elektrum_mobile_headers
from .mobilly_auth import (
    MOBILLY_API_URL,
    MOBILLY_AUTH_URL,
    mobilly_access_token,
    mobilly_app_headers,
    mobilly_refresh_token,
    mobilly_token_credentials,
)
from .mobilly_data import (
    merge_app_transactions,
    merge_transactions,
    parse_app_charge_sessions,
    parse_app_transactions,
    parse_transactions_page,
)

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
    "User-Agent": "HomeAssistant ZoeNewExtended/1.14",
}
ELEKTRUM_HEADERS = elektrum_mobile_headers()
TRANSACTION_CACHE_VERSION = 1


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
        self._elektrum_month_cache: dict[
            tuple[str, str], list[dict[str, Any]]
        ] = {}
        self._transaction_store: Store[dict[str, Any]] = Store(
            hass,
            TRANSACTION_CACHE_VERSION,
            f"{DOMAIN}.charging_accounts_{entry.entry_id}",
        )
        self._transaction_cache_loaded = False

    @property
    def accounts(self) -> list[dict[str, Any]]:
        """Return a copy of all configured account records."""
        raw_accounts = self.entry.data.get(CONF_CHARGING_ACCOUNTS, [])
        if not isinstance(raw_accounts, list):
            return []
        return deduplicate_account_records(
            account for account in raw_accounts if isinstance(account, dict)
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch enabled accounts independently so one failure cannot block others."""
        await self._async_load_transaction_cache()
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
        cache_changed = False
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
                cache_changed = True
                summary.update(
                    {
                        "status": result.get("status", "ok"),
                        "error": result.get("error"),
                        "transaction_count": len(transactions),
                        "source_counts": result.get("source_counts", {}),
                    }
                )
                for key in (
                    "auth_state",
                    "profile_type",
                    "agreement_linked",
                    "agreement_count",
                ):
                    if key in result:
                        summary[key] = result[key]
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
        if cache_changed:
            await self._async_save_transaction_cache()
        return {
            "configured": bool(accounts),
            "account_count": len(accounts),
            "enabled_account_count": len(enabled),
            "accounts": account_status,
            "transactions": transactions,
            "transaction_count": len(transactions),
            "fetched_at": fetched_at,
        }

    async def _async_load_transaction_cache(self) -> None:
        """Restore exact provider history before the first live refresh."""
        if self._transaction_cache_loaded:
            return
        self._transaction_cache_loaded = True
        payload = await self._transaction_store.async_load()
        groups = (
            payload.get("transactions_by_account")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(groups, dict):
            return
        self._last_transactions_by_account = {
            str(account_id): [dict(item) for item in transactions if isinstance(item, dict)]
            for account_id, transactions in groups.items()
            if isinstance(transactions, list)
        }

    async def _async_save_transaction_cache(self) -> None:
        """Persist exact provider history without any account credentials."""
        await self._transaction_store.async_save(
            {
                "transactions_by_account": self._last_transactions_by_account,
                "saved_at": datetime.now(UTC).isoformat(),
            }
        )

    async def _async_fetch_account(
        self, account: dict[str, Any]
    ) -> dict[str, Any]:
        account_type = account.get(CONF_ACCOUNT_TYPE)
        if account_type == ACCOUNT_TYPE_MOBILLY:
            return await self._async_fetch_mobilly(account)
        if account_type == ACCOUNT_TYPE_ELEKTRUM_DRIVE:
            return await self._async_fetch_elektrum(account)
        if account_type in AMPECO_ACCOUNT_TYPES:
            return await self._async_fetch_ampeco(account)
        raise ValueError("Unsupported charging account type")

    async def _async_fetch_mobilly(
        self, account: dict[str, Any]
    ) -> dict[str, Any]:
        username = str(account.get(CONF_MOBILLY_USERNAME) or "").strip()
        password = str(account.get(CONF_MOBILLY_PASSWORD) or "")
        access_token = str(account.get(CONF_MOBILLY_ACCESS_TOKEN) or "")
        transaction_groups: list[list[dict[str, Any]]] = []
        source_counts: dict[str, int] = {}
        app_error: str | None = None

        if access_token:
            try:
                history_payload, access_token = await self._async_mobilly_get(
                    "account/transaction-history/all",
                    access_token,
                    account,
                )
                sessions_payload, access_token = await self._async_mobilly_get(
                    "ev-charge/sessions",
                    access_token,
                    account,
                )
                app_history = parse_app_transactions(history_payload)
                app_sessions = parse_app_charge_sessions(sessions_payload)
                app_transactions = merge_app_transactions(
                    app_history,
                    app_sessions,
                )
                transaction_groups.append(app_transactions)
                source_counts.update(
                    {
                        "mobilly_app_transactions": len(app_history),
                        "mobilly_app_charge_sessions": len(app_sessions),
                    }
                )
            except (ClientError, PermissionError, RuntimeError, TimeoutError) as err:
                app_error = _safe_error(err)
                _LOGGER.warning(
                    "Unable to refresh Mobilly app history for account %s: %s",
                    account.get(CONF_ACCOUNT_ID),
                    app_error,
                )

        if username and password:
            direct, mobile = await self._async_fetch_mobilly_web(username, password)
            transaction_groups.extend((direct, mobile))
            source_counts.update(
                {
                    "payments": len(direct),
                    "payments_mobile": len(mobile),
                }
            )
        elif not transaction_groups:
            if app_error:
                raise PermissionError(app_error)
            raise ValueError("Mobilly account needs web or mobile-app authentication")

        transactions = merge_transactions(*transaction_groups)
        transactions = tag_account_transactions(
            transactions,
            account_id=str(account[CONF_ACCOUNT_ID]),
            account_name=str(account.get(CONF_ACCOUNT_NAME) or "Mobilly"),
            account_type=ACCOUNT_TYPE_MOBILLY,
        )
        return {
            "transactions": transactions,
            "auth_state": "authenticated",
            "status": "partial" if app_error else "ok",
            "error": app_error,
            "source_counts": source_counts,
        }

    async def _async_fetch_mobilly_web(
        self,
        username: str,
        password: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch both legacy Mobilly web statements."""

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
        return direct, mobile

    async def _async_mobilly_get(
        self,
        path: str,
        token: str,
        account: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        payload, status = await self._async_mobilly_request(path, token)
        if status != 401:
            if status >= 400:
                raise RuntimeError(f"Mobilly app request failed ({status})")
            return payload, token

        refresh_token = str(account.get(CONF_MOBILLY_REFRESH_TOKEN) or "")
        phone = str(account.get(CONF_MOBILLY_PHONE) or "")
        if not refresh_token or not phone:
            raise PermissionError("Mobilly app session has expired")
        session = async_get_clientsession(self.hass)
        async with session.post(
            f"{MOBILLY_AUTH_URL}/token/refresh_token",
            headers=mobilly_app_headers(),
            json=mobilly_token_credentials(
                phone,
                refresh_token,
                grant_type="refresh_token",
            )["tokenCredentials"],
            timeout=REQUEST_TIMEOUT,
        ) as response:
            try:
                refresh_payload = await response.json(content_type=None)
            except (TypeError, ValueError):
                refresh_payload = {}
            refresh_status = response.status
        refreshed_token = mobilly_access_token(refresh_payload)
        if refresh_status >= 400 or not refreshed_token:
            raise PermissionError("Mobilly app session refresh failed")
        refreshed_refresh = (
            mobilly_refresh_token(refresh_payload) or refresh_token
        )
        self._store_mobilly_tokens(
            str(account.get(CONF_ACCOUNT_ID) or ""),
            refreshed_token,
            refreshed_refresh,
        )
        payload, status = await self._async_mobilly_request(
            path,
            refreshed_token,
        )
        if status >= 400:
            raise RuntimeError(f"Mobilly app request failed ({status})")
        return payload, refreshed_token

    async def _async_mobilly_request(
        self,
        path: str,
        token: str,
    ) -> tuple[dict[str, Any], int]:
        session = async_get_clientsession(self.hass)
        async with session.get(
            f"{MOBILLY_API_URL}/{path.lstrip('/')}",
            headers=mobilly_app_headers(token),
            timeout=REQUEST_TIMEOUT,
        ) as response:
            try:
                payload = await response.json(content_type=None)
            except (TypeError, ValueError):
                payload = {}
            return payload if isinstance(payload, dict) else {}, response.status

    async def _async_fetch_elektrum(
        self, account: dict[str, Any]
    ) -> dict[str, Any]:
        token = str(account.get(CONF_ELEKTRUM_ACCESS_TOKEN) or "")
        if not token:
            raise PermissionError("Elektrum Drive account needs authentication")

        account_id = str(account[CONF_ACCOUNT_ID])
        account_name = str(
            account.get(CONF_ACCOUNT_NAME) or "Elektrum Drive"
        )
        profile_payload, profile_status, token = await self._async_elektrum_get(
            "user",
            token,
            account,
        )
        if profile_status >= 400:
            raise PermissionError(
                f"Elektrum Drive profile request failed ({profile_status})"
            )
        profile_state = elektrum_profile_state(profile_payload)
        if profile_state["auth_state"] == "agreement_required":
            return {
                "transactions": [],
                **profile_state,
                "status": "action_required",
                "error": "Elektrum postpaid agreement is not linked",
                "source_counts": {"elektrum_drive_app": 0, "months": {}},
            }
        months = elektrum_month_keys(
            datetime.now(UTC),
            history_days=HISTORY_DAYS,
        )
        refresh_months = set(months[:2])
        source_counts: dict[str, int] = {}
        transaction_groups: list[list[dict[str, Any]]] = []
        legacy_payload_used = False
        for month in months:
            cache_key = (account_id, month)
            cached = self._elektrum_month_cache.get(cache_key)
            if cached is not None and month not in refresh_months:
                transaction_groups.append(cached)
                source_counts[month] = len(cached)
                continue

            payload, status, token = await self._async_elektrum_get(
                "transactions",
                token,
                account,
                params={"date": month},
            )
            if status == 404:
                # Older service releases did not support the month parameter.
                if legacy_payload_used:
                    break
                payload, status, token = await self._async_elektrum_get(
                    "transactions",
                    token,
                    account,
                )
                legacy_payload_used = True
            if status >= 400:
                raise PermissionError(
                    f"Elektrum Drive request failed ({status})"
                )
            parsed = parse_elektrum_transactions(
                payload,
                account_id=account_id,
                account_name=account_name,
            )
            self._elektrum_month_cache[cache_key] = parsed
            transaction_groups.append(parsed)
            source_counts[month] = len(parsed)
            if legacy_payload_used:
                break

        transactions = merge_account_transactions(*transaction_groups)
        return {
            "transactions": transactions,
            **profile_state,
            "source_counts": {
                "elektrum_drive_app": len(transactions),
                "months": source_counts,
            },
        }

    async def _async_elektrum_get(
        self,
        path: str,
        token: str,
        account: dict[str, Any],
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], int, str]:
        """Run one authenticated GET and transparently refresh its token."""
        payload, status = await self._async_elektrum_request(
            path,
            token,
            params=params,
        )
        if status != 401:
            return payload, status, token

        refresh_payload, refresh_status = await self._async_elektrum_request(
            "auth/refresh",
            token,
        )
        if refresh_status >= 400:
            raise PermissionError("Elektrum Drive session has expired")
        refreshed_token = _access_token(refresh_payload)
        if not refreshed_token:
            raise PermissionError("Elektrum Drive did not return a new token")
        if account.get(CONF_ELEKTRUM_AGREEMENT_ID):
            profile_payload, profile_status = await self._async_elektrum_request(
                "user",
                refreshed_token,
            )
            if profile_status >= 400 or not elektrum_token_can_replace(
                None,
                profile_payload,
                saved_agreement=True,
            ):
                raise PermissionError(
                    "Elektrum Drive refreshed into an unlinked app profile"
                )
        self._store_refreshed_token(
            str(account[CONF_ACCOUNT_ID]),
            refreshed_token,
            str(account.get(CONF_ELEKTRUM_DEVICE_UUID) or ""),
        )
        payload, status = await self._async_elektrum_request(
            path,
            refreshed_token,
            params=params,
        )
        return payload, status, refreshed_token

    async def _async_elektrum_request(
        self,
        path: str,
        token: str,
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], int]:
        headers = {**ELEKTRUM_HEADERS, "Authorization": f"Bearer {token}"}
        async with ClientSession(
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        ) as session:
            async with session.get(
                f"{ELEKTRUM_API_URL}/{path}",
                params=params,
            ) as response:
                status = response.status
                try:
                    payload = await response.json(content_type=None)
                except (TypeError, ValueError):
                    payload = {}
        return payload if isinstance(payload, dict) else {}, status

    async def _async_fetch_ampeco(
        self,
        account: dict[str, Any],
    ) -> dict[str, Any]:
        """Fetch every public charging session from one AMPECO app profile."""
        provider = ampeco_provider(account.get(CONF_ACCOUNT_TYPE))
        token = str(account.get(CONF_AMPECO_ACCESS_TOKEN) or "")
        if not token:
            raise PermissionError(
                f"{provider.display_name} account needs authentication"
            )

        account_id = str(account[CONF_ACCOUNT_ID])
        account_name = str(
            account.get(CONF_ACCOUNT_NAME) or provider.display_name
        )
        date_to = datetime.now(UTC).date()
        date_from = date_to - timedelta(days=HISTORY_DAYS)
        per_page = 100
        raw_records: list[dict[str, Any]] = []
        page_counts: dict[str, int] = {}
        for page in range(1, 51):
            payload, status, token = await self._async_ampeco_get(
                provider,
                "profile/session_history",
                token,
                account,
                params={
                    "start_date": date_from.isoformat(),
                    "end_date": date_to.isoformat(),
                    "page": str(page),
                    "perPage": str(per_page),
                    "sessionType": "public",
                    "operatorCountry": provider.operator_country,
                },
            )
            if status >= 400:
                raise PermissionError(
                    f"{provider.display_name} history request failed ({status})"
                )
            items, has_more = ampeco_history_page(
                payload,
                page=page,
                per_page=per_page,
            )
            raw_records.extend(items)
            page_counts[str(page)] = len(items)
            if not has_more:
                break

        transactions = parse_ampeco_transactions(
            raw_records,
            account_id=account_id,
            account_name=account_name,
            account_type=provider.account_type,
            provider_name=provider.display_name,
        )
        transactions = merge_account_transactions(transactions)
        return {
            "transactions": transactions,
            "auth_state": "authenticated",
            "source_counts": {
                f"{provider.account_type}_app": len(transactions),
                "raw_sessions": len(raw_records),
                "pages": page_counts,
            },
        }

    async def _async_ampeco_get(
        self,
        provider,
        path: str,
        token: str,
        account: dict[str, Any],
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[Any, int, str]:
        """Run an authenticated AMPECO request and refresh once on expiry."""
        payload, status = await self._async_ampeco_request(
            provider,
            path,
            token,
            params=params,
        )
        if status != 401:
            return payload, status, token

        refresh_token = str(account.get(CONF_AMPECO_REFRESH_TOKEN) or "")
        if not refresh_token:
            raise PermissionError(
                f"{provider.display_name} app session has expired"
            )
        session = async_get_clientsession(self.hass)
        async with session.post(
            f"https://{provider.host}/api/v1/app/oauth/token",
            params={"operatorCountry": provider.operator_country},
            headers=ampeco_app_headers(provider),
            json=ampeco_token_form(
                provider,
                grant_type="refresh_token",
                token=refresh_token,
            ),
            timeout=REQUEST_TIMEOUT,
        ) as response:
            try:
                refresh_payload = await response.json(content_type=None)
            except (TypeError, ValueError):
                refresh_payload = {}
            refresh_status = response.status
        token_values = ampeco_token_values(refresh_payload)
        refreshed_token = str(token_values.get("access_token") or "")
        if refresh_status >= 400 or not refreshed_token:
            raise PermissionError(
                f"{provider.display_name} app session refresh failed"
            )
        refreshed_refresh = str(
            token_values.get("refresh_token") or refresh_token
        )
        self._store_ampeco_tokens(
            str(account.get(CONF_ACCOUNT_ID) or ""),
            refreshed_token,
            refreshed_refresh,
            str(token_values.get("expires_at") or ""),
        )
        payload, status = await self._async_ampeco_request(
            provider,
            path,
            refreshed_token,
            params=params,
        )
        return payload, status, refreshed_token

    async def _async_ampeco_request(
        self,
        provider,
        path: str,
        token: str,
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[Any, int]:
        session = async_get_clientsession(self.hass)
        async with session.get(
            f"https://{provider.host}/api/v1/app/{path.lstrip('/')}",
            params=params,
            headers=ampeco_app_headers(provider, token),
            timeout=REQUEST_TIMEOUT,
        ) as response:
            try:
                payload = await response.json(content_type=None)
            except (TypeError, ValueError):
                payload = {}
            status = response.status
        return payload if isinstance(payload, (dict, list)) else {}, status

    def _store_mobilly_tokens(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
    ) -> None:
        accounts = self.accounts
        changed = False
        for account in accounts:
            if str(account.get(CONF_ACCOUNT_ID)) != account_id:
                continue
            account[CONF_MOBILLY_ACCESS_TOKEN] = access_token
            account[CONF_MOBILLY_REFRESH_TOKEN] = refresh_token
            changed = True
            break
        if not changed:
            return
        data = dict(self.entry.data)
        data[CONF_CHARGING_ACCOUNTS] = accounts
        self.hass.config_entries.async_update_entry(self.entry, data=data)

    def _store_ampeco_tokens(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: str,
    ) -> None:
        accounts = self.accounts
        changed = False
        for account in accounts:
            if str(account.get(CONF_ACCOUNT_ID)) != account_id:
                continue
            account[CONF_AMPECO_ACCESS_TOKEN] = access_token
            account[CONF_AMPECO_REFRESH_TOKEN] = refresh_token
            if expires_at:
                account[CONF_AMPECO_TOKEN_EXPIRES_AT] = expires_at
            changed = True
            break
        if not changed:
            return
        data = dict(self.entry.data)
        data[CONF_CHARGING_ACCOUNTS] = accounts
        self.hass.config_entries.async_update_entry(self.entry, data=data)

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
    if isinstance(data, dict):
        value = (
            data.get("accessToken")
            or data.get("access_token")
            or data.get("token")
        )
    else:
        value = (
            payload.get("accessToken")
            or payload.get("access_token")
            or payload.get("token")
        )
    return str(value) if value else None


def _safe_error(error: Exception) -> str:
    if isinstance(error, ClientResponseError):
        return f"HTTP {error.status}"
    if isinstance(error, (ClientError, TimeoutError)):
        return type(error).__name__
    return str(error)[:160] or type(error).__name__
