"""Pure helpers for the Elektrum Drive Smart-ID authorization flow."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import re
from typing import Any


class _AuthenticationFormParser(HTMLParser):
    """Extract the short-lived identity token from Elektrum's form."""

    def __init__(self) -> None:
        super().__init__()
        self.token = ""

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self.token:
            return
        attributes = dict(attrs)
        classes = set(str(attributes.get("class") or "").split())
        if "authentication-form" in classes:
            self.token = str(attributes.get("data-token") or "").strip()


def extract_authentication_token(html: str) -> str:
    """Return the identity token embedded in an Elektrum authentication page."""
    parser = _AuthenticationFormParser()
    parser.feed(html)
    return parser.token


def nested_value(payload: Any, *keys: str) -> str:
    """Find the first non-empty value by key in a nested API response."""
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if value is not None and not isinstance(value, (dict, list)):
                text = str(value).strip()
                if text:
                    return text
        for value in payload.values():
            result = nested_value(value, *keys)
            if result:
                return result
    elif isinstance(payload, list):
        for value in payload:
            result = nested_value(value, *keys)
            if result:
                return result
    return ""


def verification_code(payload: Any) -> str:
    """Return the Smart-ID verification code without logging personal data."""
    return nested_value(payload, "verificationCode", "verification_code")


def authenticated_personal_code(payload: Any) -> str:
    """Return the identity-confirmed code from the Smart-ID poll response."""
    return nested_value(
        payload,
        "personalCode",
        "personal_code",
        "identifier",
    )


def personal_code_candidates(value: Any) -> tuple[str, ...]:
    """Return the verified callback unchanged, then normalized fallbacks."""
    raw = str(value or "").strip()
    digits = "".join(
        character
        for character in raw
        if character.isascii() and character.isdigit()
    )
    if len(digits) != 11:
        return ()
    hyphenated = f"{digits[:6]}-{digits[6:]}"
    candidates = []
    if raw not in {digits, hyphenated}:
        candidates.append(raw)
    candidates.extend((hyphenated, digits))
    return tuple(dict.fromkeys(candidates))


def personal_code_format(value: Any) -> str:
    """Describe a personal-code shape without exposing personal data."""
    raw = str(value or "").strip()
    if not raw:
        return "empty"
    digits = sum(character.isascii() and character.isdigit() for character in raw)
    letters = sum(character.isascii() and character.isalpha() for character in raw)
    separators = len(raw) - digits - letters
    return f"length={len(raw)},digits={digits},letters={letters},separators={separators}"


_AUTH_SUCCESS_RE = re.compile(
    r"(?:authenticationSuccess(?:\.postMessage)?\s*\()\s*(.+?)\s*\)\s*;",
    re.DOTALL,
)
_PERSONAL_CODE_RE = re.compile(
    r'["\']personalCode["\']\s*:\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


class _ScriptParser(HTMLParser):
    """Collect inline scripts from Elektrum's authentication callback page."""

    def __init__(self) -> None:
        super().__init__()
        self._in_script = False
        self._parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() == "script":
            self._in_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self._in_script = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._parts.append(data)

    @property
    def script(self) -> str:
        return "\n".join(self._parts)


def authentication_complete_personal_code(html: str) -> str:
    """Extract the identity-confirmed personal code from Elektrum's callback."""
    parser = _ScriptParser()
    parser.feed(html)
    script = parser.script

    for match in _AUTH_SUCCESS_RE.finditer(script):
        argument = match.group(1).strip()
        candidates = [argument]
        try:
            decoded = json.loads(argument)
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, str):
            candidates.append(decoded)
        elif isinstance(decoded, dict):
            value = authenticated_personal_code(decoded)
            if value:
                return value

        for candidate in candidates:
            code_match = _PERSONAL_CODE_RE.search(candidate)
            if code_match:
                return code_match.group(1).strip()

    return ""
