"""Pure helpers for Mobilly mobile-app authentication."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any


MOBILLY_API_URL = "https://api.mobilly.lv/v3"
MOBILLY_AUTH_URL = "https://auth.mobilly.lv"
MOBILLY_APP_VERSION = "30.0.4"
# This is the public application identifier bundled in Mobilly's Android app.
MOBILLY_ANDROID_APPLICATION_ID = "AAghe7tie6AiWai8ahLem8ienahte7no"
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def normalize_mobilly_phone(value: Any) -> str:
    """Return the international digits-only phone format used by the app."""
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) == 8:
        return f"371{digits}"
    if digits.startswith("00"):
        return digits[2:]
    return digits


def mobilly_token_credentials(
    phone: str,
    password: str,
    *,
    grant_type: str,
) -> dict[str, Any]:
    """Build the token request used by the official Android client."""
    return {
        "grantType": grant_type,
        "tokenCredentials": {
            "password": password,
            "userId": normalize_mobilly_phone(phone),
            "applicationId": MOBILLY_ANDROID_APPLICATION_ID,
            "accountType": "client",
        },
    }


def mobilly_access_token(payload: Mapping[str, Any] | None) -> str:
    """Extract an access token from direct or wrapped auth responses."""
    return _find_token(payload, ("accessToken", "access_token", "token"))


def mobilly_refresh_token(payload: Mapping[str, Any] | None) -> str:
    """Extract a refresh token from direct or wrapped auth responses."""
    return _find_token(
        payload,
        ("refreshToken", "refresh_token", "refreshableToken"),
        allow_mapping=False,
    )


def mobilly_request_timestamp(now: datetime | None = None) -> str:
    """Return the JavaScript Date.toString-style timestamp used by the app."""
    value = now or datetime.now().astimezone()
    if value.tzinfo is None:
        value = value.astimezone()
    offset = value.strftime("%z") or "+0000"
    return (
        f"{_WEEKDAYS[value.weekday()]} {_MONTHS[value.month - 1]} "
        f"{value.day:02d} {value.year:04d} {value:%H:%M:%S} GMT{offset}"
    )


def mobilly_app_headers(access_token: str = "") -> dict[str, str]:
    """Return the stable request identity expected by Mobilly's app API."""
    headers = {
        "Accept": "application/json",
        "Accept-Language": "lv",
        "Origin": "https://localhost",
        "User-Agent": "HomeAssistant ZoeNewExtended/1.16",
        "Mobilly-Os": "Android",
        "Mobilly-Os-Version": "14",
        "Mobilly-App-Version": MOBILLY_APP_VERSION,
        "Mobilly-Device-Brand": "Home Assistant",
        "Mobilly-Device-Model": "Zoe New Extended",
        "Mobilly-Device": "Home Assistant",
        "Mobilly-Device-Carrier": "",
        "Mobilly-Request-Timestamp": mobilly_request_timestamp(),
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _find_token(
    value: Any,
    names: tuple[str, ...],
    *,
    allow_mapping: bool = True,
) -> str:
    if not isinstance(value, Mapping):
        return ""
    for name in names:
        candidate = value.get(name)
        if isinstance(candidate, str) and candidate:
            return candidate
        if allow_mapping and isinstance(candidate, Mapping):
            nested = _find_token(candidate, names, allow_mapping=allow_mapping)
            if nested:
                return nested
    for wrapper in ("data", "result", "refreshableToken", "tokens"):
        nested = value.get(wrapper)
        if isinstance(nested, Mapping):
            token = _find_token(nested, names, allow_mapping=allow_mapping)
            if token:
                return token
    return ""
