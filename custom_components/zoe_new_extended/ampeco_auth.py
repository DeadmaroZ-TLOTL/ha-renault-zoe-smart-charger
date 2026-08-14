"""Shared AMPECO app configuration and authentication helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True, slots=True)
class AmpecoProviderConfig:
    """Configuration published in an operator's official mobile app."""

    account_type: str
    display_name: str
    provider: str
    provider_group: str
    host: str
    operator_country: str
    app_bundle_id: str
    app_version: str
    oauth_client_id: str
    oauth_client_secret: str


# AMPECO mobile clients are public OAuth clients. These identifiers are part of
# the official APKs and cannot be treated as confidential application secrets.
IGNITIS_ON = AmpecoProviderConfig(
    account_type="ignitis_on",
    display_name="Ignitis ON",
    provider="ignitis_on",
    provider_group="ignitis",
    host="ignitis.eu-ignitis.charge.ampeco.tech",
    operator_country="LV",
    app_bundle_id="com.fortum.chargeiton",
    app_version="8.182.0",
    oauth_client_id="1",
    oauth_client_secret="vTmcxpfek5iM7S56FATz3kv7sxFqRVKVzSMpIIeO",
)

IKRAUTAS = AmpecoProviderConfig(
    account_type="ikrautas",
    display_name="IKRAUTAS",
    provider="ikrautas",
    provider_group="ikrautas",
    host="ikrautas.eu.charge.ampeco.tech",
    operator_country="LT",
    app_bundle_id="lt.ikrautas.cp.app",
    app_version="3.149.1",
    oauth_client_id="1",
    oauth_client_secret="9Etafh8OBHdJrIKFV52twYMltNLg1OdvVKFSPLug",
)

AMPECO_PROVIDERS = {
    IGNITIS_ON.account_type: IGNITIS_ON,
    IKRAUTAS.account_type: IKRAUTAS,
}
AMPECO_ACCOUNT_TYPES = frozenset(AMPECO_PROVIDERS)


def ampeco_provider(account_type: Any) -> AmpecoProviderConfig:
    """Return the supported provider configuration for an account type."""
    try:
        return AMPECO_PROVIDERS[str(account_type)]
    except KeyError as err:
        raise ValueError("Unsupported AMPECO account type") from err


def ampeco_app_headers(
    provider: AmpecoProviderConfig,
    access_token: str | None = None,
) -> dict[str, str]:
    """Return headers used by the provider's official Android client."""
    device_id = uuid5(
        NAMESPACE_URL,
        f"https://{provider.host}/{provider.app_bundle_id}/home-assistant",
    )
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en",
        "Content-Type": "application/json",
        "User-Agent": "okhttp/4.12.0",
        "X-Platform": "android",
        "x-device-id": str(device_id),
        "x-operator-country": provider.operator_country,
        "x-mobile-app-bundle-id": provider.app_bundle_id,
        "X-Internal-App-Version": provider.app_version,
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def ampeco_login_link_requested(payload: Any) -> bool:
    """Validate that a login-link request was accepted by the tenant."""
    if not isinstance(payload, dict):
        return False
    data: Any = payload.get("data", payload)
    if isinstance(data, bool):
        return data
    if not isinstance(data, dict):
        return payload.get("success") is True

    if data.get("success") is True or data.get("sent") is True:
        return True
    if data.get("activeLoginLink"):
        return True
    if data.get("email") and (
        data.get("createdAt")
        or data.get("created_at")
        or data.get("lifetimeInMinutes")
    ):
        return True
    status = str(data.get("status") or payload.get("status") or "").lower()
    return status in {"accepted", "ok", "sent", "success"}


def ampeco_login_link_token(value: Any) -> str | None:
    """Extract a one-time token from a copied AMPECO email login link."""
    text = unquote(str(value or "").strip())
    if not text:
        return None

    parsed = urlparse(text)
    containers = [parsed.query, parsed.fragment]
    if "?" in parsed.fragment:
        containers.append(parsed.fragment.split("?", 1)[1])
    for raw_query in containers:
        values = parse_qs(raw_query, keep_blank_values=False)
        for key in (
            "token",
            "login_token",
            "loginToken",
            "login-link-token",
            "loginLinkToken",
            "code",
        ):
            candidate = next(iter(values.get(key, [])), "").strip()
            if candidate:
                return candidate

    if parsed.scheme and parsed.path:
        candidate = parsed.path.rstrip("/").rsplit("/", 1)[-1].strip()
        if len(candidate) >= 16:
            return candidate
    if not parsed.scheme and not any(character.isspace() for character in text):
        return text
    return None


def ampeco_token_values(payload: Any) -> dict[str, Any]:
    """Normalize an OAuth token response returned by an AMPECO tenant."""
    if not isinstance(payload, dict):
        return {}
    data: Any = payload.get("data", payload)
    if isinstance(data, dict) and isinstance(data.get("token"), dict):
        data = data["token"]
    if not isinstance(data, dict):
        return {}

    access_token = data.get("access_token") or data.get("accessToken")
    refresh_token = data.get("refresh_token") or data.get("refreshToken")
    expires_in = _as_float(data.get("expires_in") or data.get("expiresIn"))
    expires_at = data.get("expires_at") or data.get("expiresAt")
    if not expires_at and expires_in is not None:
        expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()
    return {
        "access_token": str(access_token) if access_token else None,
        "refresh_token": str(refresh_token) if refresh_token else None,
        "expires_at": str(expires_at) if expires_at else None,
    }


def ampeco_token_form(
    provider: AmpecoProviderConfig,
    *,
    grant_type: str,
    token: str,
    login_type: str | None = None,
) -> dict[str, str]:
    """Build the official app's OAuth request body."""
    result = {
        "client_id": provider.oauth_client_id,
        "client_secret": provider.oauth_client_secret,
        "grant_type": grant_type,
    }
    if grant_type == "refresh_token":
        result["refresh_token"] = token
    else:
        result["token"] = token
        result["operatorCountry"] = provider.operator_country
        if login_type:
            result["type"] = login_type
    return result


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
