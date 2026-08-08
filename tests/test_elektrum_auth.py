"""Tests for Elektrum Smart-ID response parsing."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "elektrum_auth.py"
)
SPEC = importlib.util.spec_from_file_location("elektrum_auth", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
elektrum_auth = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(elektrum_auth)

authenticated_personal_code = elektrum_auth.authenticated_personal_code
authentication_complete_personal_code = (
    elektrum_auth.authentication_complete_personal_code
)
extract_authentication_token = elektrum_auth.extract_authentication_token
personal_code_candidates = elektrum_auth.personal_code_candidates
personal_code_format = elektrum_auth.personal_code_format
verification_code = elektrum_auth.verification_code


class ElektrumAuthHelpersTest(unittest.TestCase):
    def test_extract_authentication_token(self):
        html = (
            '<main class="authentication-form extra" data-token="short-lived">'
            "</main>"
        )
        self.assertEqual(extract_authentication_token(html), "short-lived")

    def test_missing_authentication_token(self):
        self.assertEqual(extract_authentication_token("<main></main>"), "")

    def test_verification_code_from_wrapper(self):
        self.assertEqual(
            verification_code({"data": {"verificationCode": "1234"}}),
            "1234",
        )

    def test_authenticated_personal_code_from_root(self):
        self.assertEqual(
            authenticated_personal_code({"personalCode": "01010112345"}),
            "01010112345",
        )

    def test_authenticated_personal_code_from_elektrum_poll_identifier(self):
        self.assertEqual(
            authenticated_personal_code(
                {
                    "firstName": "Test",
                    "lastName": "User",
                    "identifier": "010101-12345",
                    "authenticationType": "SmartId",
                }
            ),
            "010101-12345",
        )

    def test_personal_code_candidates_use_official_format_first(self):
        self.assertEqual(
            personal_code_candidates("01010112345"),
            ("010101-12345", "01010112345"),
        )

    def test_personal_code_candidates_normalize_callback(self):
        self.assertEqual(
            personal_code_candidates("010101-12345"),
            ("010101-12345", "01010112345"),
        )

    def test_personal_code_candidates_reject_invalid_value(self):
        self.assertEqual(personal_code_candidates("123"), ())

    def test_personal_code_candidates_preserve_identity_callback(self):
        self.assertEqual(
            personal_code_candidates("LV-010101-12345"),
            ("LV-010101-12345", "010101-12345", "01010112345"),
        )

    def test_personal_code_format_does_not_expose_value(self):
        self.assertEqual(
            personal_code_format("LV-010101-12345"),
            "length=15,digits=11,letters=2,separators=2",
        )

    def test_deeply_nested_response_values(self):
        self.assertEqual(
            verification_code(
                {"data": {"result": {"verificationCode": "1234"}}}
            ),
            "1234",
        )

    def test_complete_page_object_callback(self):
        html = """
        <html><script>
        App.authenticationSuccess({"personalCode":"010101-12345"});
        </script></html>
        """
        self.assertEqual(
            authentication_complete_personal_code(html),
            "010101-12345",
        )

    def test_complete_page_string_callback(self):
        html = r"""
        <html><script>
        window.webkit.messageHandlers.authenticationSuccess.postMessage(
          '{"personalCode":"010101-12345"}'
        );
        </script></html>
        """
        self.assertEqual(
            authentication_complete_personal_code(html),
            "010101-12345",
        )

    def test_complete_page_failure_has_no_code(self):
        html = "<script>App.authenticationFailure();</script>"
        self.assertEqual(authentication_complete_personal_code(html), "")


if __name__ == "__main__":
    unittest.main()
