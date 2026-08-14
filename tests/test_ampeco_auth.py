"""Tests for AMPECO account authentication helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "ampeco_auth.py"
)
SPEC = importlib.util.spec_from_file_location("ampeco_auth_tests", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ampeco_auth = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ampeco_auth
SPEC.loader.exec_module(ampeco_auth)


class AmpecoAuthTest(unittest.TestCase):
    """Verify login links and OAuth responses are handled without persistence."""

    def test_official_app_versions_and_headers(self) -> None:
        self.assertEqual("8.182.0", ampeco_auth.IGNITIS_ON.app_version)
        self.assertEqual("3.149.1", ampeco_auth.IKRAUTAS.app_version)

        headers = ampeco_auth.ampeco_app_headers(ampeco_auth.IGNITIS_ON)
        self.assertEqual("8.182.0", headers["X-Internal-App-Version"])
        self.assertEqual("android", headers["X-Platform"])
        self.assertTrue(headers["x-device-id"])

    def test_login_request_requires_server_confirmation(self) -> None:
        self.assertTrue(
            ampeco_auth.ampeco_login_link_requested(
                {"data": {"status": "sent"}}
            )
        )
        self.assertTrue(
            ampeco_auth.ampeco_login_link_requested({"success": True})
        )
        self.assertTrue(
            ampeco_auth.ampeco_login_link_requested(
                {
                    "data": {
                        "email": "user@example.com",
                        "createdAt": "2026-08-13T12:00:00Z",
                        "lifetimeInMinutes": 15,
                    }
                }
            )
        )
        self.assertFalse(ampeco_auth.ampeco_login_link_requested({"data": {}}))
        self.assertFalse(ampeco_auth.ampeco_login_link_requested({}))

    def test_extracts_login_token_from_supported_link_forms(self) -> None:
        self.assertEqual(
            "abc123token456789",
            ampeco_auth.ampeco_login_link_token(
                "https://cp.example/login?token=abc123token456789"
            ),
        )
        self.assertEqual(
            "fragment-token-1234",
            ampeco_auth.ampeco_login_link_token(
                "ampeco://login#loginToken=fragment-token-1234"
            ),
        )
        self.assertEqual(
            "raw-token-123456",
            ampeco_auth.ampeco_login_link_token("raw-token-123456"),
        )

    def test_normalizes_nested_token_payload(self) -> None:
        values = ampeco_auth.ampeco_token_values(
            {
                "data": {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                }
            }
        )
        self.assertEqual("access", values["access_token"])
        self.assertEqual("refresh", values["refresh_token"])
        self.assertTrue(values["expires_at"])

    def test_refresh_form_uses_refresh_token_key(self) -> None:
        form = ampeco_auth.ampeco_token_form(
            ampeco_auth.IKRAUTAS,
            grant_type="refresh_token",
            token="refresh-value",
        )
        self.assertEqual("refresh-value", form["refresh_token"])
        self.assertNotIn("token", form)

    def test_google_form_matches_official_third_party_login(self) -> None:
        form = ampeco_auth.ampeco_token_form(
            ampeco_auth.IKRAUTAS,
            grant_type="third-party",
            token="google-access-token",
            login_type="google",
        )

        self.assertEqual("third-party", form["grant_type"])
        self.assertEqual("google-access-token", form["token"])
        self.assertEqual("google", form["type"])
        self.assertEqual("LT", form["operatorCountry"])


if __name__ == "__main__":
    unittest.main()
