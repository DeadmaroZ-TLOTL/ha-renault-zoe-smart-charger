"""Tests for the Elektrum Drive mobile login helpers."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "elektrum_login.py"
)
SPEC = importlib.util.spec_from_file_location("elektrum_login", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
elektrum_login = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(elektrum_login)


class ElektrumLoginTest(unittest.TestCase):
    """Verify requests match the official Android client."""

    def test_normalizes_local_and_international_phone(self) -> None:
        self.assertEqual(
            elektrum_login.normalize_elektrum_phone("00 000 000"),
            "00000000",
        )
        self.assertEqual(
            elektrum_login.normalize_elektrum_phone("+371 00 000 000"),
            "00000000",
        )

    def test_builds_official_sms_form(self) -> None:
        form = elektrum_login.elektrum_sms_form(
            "+371 00 000 000",
            "+371",
            "06e73fcf-5ffc-499d-9888-b2a6f495e83b",
            "captcha-token",
        )

        self.assertEqual(
            form,
            {
                "phone": "00000000",
                "language": "lv",
                "countryId": elektrum_login.ELEKTRUM_LATVIA_COUNTRY_ID,
                "countryCode": "371",
                "deviceUUID": "06e73fcf-5ffc-499d-9888-b2a6f495e83b",
                "deviceType": "2",
                "captchaSolution": "captcha-token",
            },
        )

    def test_builds_official_verify_form(self) -> None:
        self.assertEqual(
            elektrum_login.elektrum_verify_form(
                "+37100000000",
                "12 34",
                "371",
                "device-id",
            ),
            {
                "phone": "00000000",
                "verifyCode": "1234",
                "countryCode": "371",
                "deviceUUID": "device-id",
            },
        )

    def test_extracts_mobile_access_token(self) -> None:
        self.assertEqual(
            elektrum_login.elektrum_login_token(
                {"data": {"accessToken": "token-value"}}
            ),
            "token-value",
        )
        self.assertEqual(elektrum_login.elektrum_login_token({}), "")

    def test_parses_linked_session_from_official_app_link(self) -> None:
        session = elektrum_login.parse_elektrum_app_link(
            "elektrumdrive://app/open?access_token=linked%2Btoken"
            "&phone_number=%2B37100000000"
            "&deviceUuid=06e73fcf-5ffc-499d-9888-b2a6f495e83b"
        )

        self.assertEqual(session["access_token"], "linked+token")
        self.assertEqual(session["phone"], "+37100000000")
        self.assertEqual(
            session["device_uuid"],
            "06e73fcf-5ffc-499d-9888-b2a6f495e83b",
        )

    def test_accepts_android_parameter_aliases(self) -> None:
        session = elektrum_login.parse_elektrum_app_link(
            "elektrumdrive://app/open/?accessToken=token"
            "&phoneNumber=00000000&deviceUUID=device-id"
        )

        self.assertEqual(
            session,
            {
                "access_token": "token",
                "phone": "00000000",
                "device_uuid": "device-id",
            },
        )

    def test_rejects_unrelated_or_incomplete_app_links(self) -> None:
        for value in (
            "https://example.test/open?access_token=token&deviceUuid=device-id",
            "elektrumdrive://app/open?access_token=token",
            "token-only",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                elektrum_login.parse_elektrum_app_link(value)

    def test_uses_current_android_client_headers(self) -> None:
        headers = elektrum_login.elektrum_mobile_headers("lv")
        self.assertEqual(headers["Accept-Language"], "lv")
        self.assertTrue(headers["User-Agent"].startswith("Elektrum/2.11.0 "))


if __name__ == "__main__":
    unittest.main()
