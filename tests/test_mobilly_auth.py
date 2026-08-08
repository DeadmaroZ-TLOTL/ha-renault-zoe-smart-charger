"""Tests for Mobilly app authentication helpers."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "mobilly_auth.py"
)
SPEC = importlib.util.spec_from_file_location("mobilly_auth", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
mobilly_auth = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mobilly_auth)


class MobillyAuthTest(unittest.TestCase):
    def test_normalizes_latvian_local_number(self) -> None:
        self.assertEqual(
            "37120000000",
            mobilly_auth.normalize_mobilly_phone("20 000 000"),
        )

    def test_builds_official_otp_credentials(self) -> None:
        result = mobilly_auth.mobilly_token_credentials(
            "+37120000000",
            "1234",
            grant_type="otp",
        )

        self.assertEqual("otp", result["grantType"])
        self.assertEqual("37120000000", result["tokenCredentials"]["userId"])
        self.assertEqual("1234", result["tokenCredentials"]["password"])
        self.assertEqual("client", result["tokenCredentials"]["accountType"])

    def test_extracts_nested_refreshable_tokens(self) -> None:
        payload = {
            "data": {
                "refreshableToken": {
                    "accessToken": "access",
                    "refreshToken": "refresh",
                }
            }
        }

        self.assertEqual("access", mobilly_auth.mobilly_access_token(payload))
        self.assertEqual("refresh", mobilly_auth.mobilly_refresh_token(payload))

    def test_uses_the_mobile_apps_timestamp_format(self) -> None:
        timestamp = mobilly_auth.mobilly_request_timestamp(
            datetime(2026, 8, 6, 21, 15, 30, tzinfo=timezone(timedelta(hours=3)))
        )

        self.assertEqual("Thu Aug 06 2026 21:15:30 GMT+0300", timestamp)
        self.assertFalse(timestamp.isdigit())


if __name__ == "__main__":
    unittest.main()
