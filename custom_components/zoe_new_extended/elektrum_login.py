"""Helpers for the official Elektrum Drive mobile login flow."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ELEKTRUM_LATVIA_COUNTRY_ID = "067d8613-b4ef-4db5-977c-810a942aa3c4"
ELEKTRUM_MOBILE_VERSION = "2.11.0"


def normalize_elektrum_phone(value: object, country_code: object = "371") -> str:
    """Return the national number expected by the Drive mobile API."""
    digits = "".join(character for character in str(value or "") if character.isdigit())
    prefix = "".join(
        character for character in str(country_code or "") if character.isdigit()
    )
    if prefix and digits.startswith(prefix) and len(digits) > len(prefix):
        digits = digits[len(prefix) :]
    return digits


def elektrum_mobile_headers(language: str = "lv") -> dict[str, str]:
    """Build the headers sent by the official Android client."""
    locale = str(language or "lv").lower()
    return {
        "Accept": "application/json",
        "Accept-Language": locale,
        "User-Agent": (
            f"Elektrum/{ELEKTRUM_MOBILE_VERSION} "
            f"(Language: {locale}; OS: Android)"
        ),
    }


def elektrum_sms_form(
    phone: object,
    country_code: object,
    device_uuid: object,
    captcha_solution: object,
    *,
    language: str = "lv",
) -> dict[str, str]:
    """Build the form used by ``POST auth/sms``."""
    code = "".join(
        character for character in str(country_code or "") if character.isdigit()
    )
    return {
        "phone": normalize_elektrum_phone(phone, code),
        "language": str(language or "lv").lower(),
        "countryId": ELEKTRUM_LATVIA_COUNTRY_ID,
        "countryCode": code,
        "deviceUUID": str(device_uuid or "").strip(),
        "deviceType": "2",
        "captchaSolution": str(captcha_solution or "").strip(),
    }


def elektrum_verify_form(
    phone: object,
    verify_code: object,
    country_code: object,
    device_uuid: object,
) -> dict[str, str]:
    """Build the form used by ``POST auth/verify``."""
    code = "".join(
        character for character in str(country_code or "") if character.isdigit()
    )
    return {
        "phone": normalize_elektrum_phone(phone, code),
        "verifyCode": "".join(
            character
            for character in str(verify_code or "")
            if character.isdigit()
        ),
        "countryCode": code,
        "deviceUUID": str(device_uuid or "").strip(),
    }


def elektrum_login_token(payload: Mapping[str, Any] | None) -> str:
    """Extract the access token returned by ``auth/verify``."""
    if not isinstance(payload, Mapping):
        return ""
    data = payload.get("data")
    if isinstance(data, Mapping):
        token = data.get("accessToken") or data.get("access_token")
        if token:
            return str(token)
    return str(payload.get("accessToken") or payload.get("access_token") or "")
