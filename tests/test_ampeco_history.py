"""Tests for exact Ignitis ON and IKRAUTAS charging history."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "ampeco_history.py"
)
SPEC = importlib.util.spec_from_file_location("ampeco_history_tests", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ampeco_history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ampeco_history)


class AmpecoHistoryTest(unittest.TestCase):
    """Verify pagination and provider-reported totals are preserved."""

    def test_extracts_nested_page_and_pagination(self) -> None:
        records, has_more = ampeco_history.ampeco_history_page(
            {
                "data": {"sessions": [{"id": 1}, {"id": 2}]},
                "meta": {"current_page": 1, "last_page": 2},
            },
            page=1,
            per_page=100,
        )
        self.assertEqual([1, 2], [item["id"] for item in records])
        self.assertTrue(has_more)

    def test_normalizes_exact_energy_cost_and_station(self) -> None:
        records = ampeco_history.parse_ampeco_transactions(
            [
                {
                    "id": "session-42",
                    "startedAt": "2026-08-04T12:45:00+03:00",
                    "stoppedAt": "2026-08-04T14:24:00+03:00",
                    "energy": {"value": 11.17, "unit": "kWh"},
                    "totalAmount": {"withTax": 2.42, "currency": "EUR"},
                    "status": "completed",
                    "location": {
                        "id": 77,
                        "name": "Laivu iela 32",
                        "address": "Carnikava, Latvia",
                    },
                    "evse": {"emi3Identifier": "LV*TEST*E1"},
                }
            ],
            account_id="account-1",
            account_name="Ignitis personal",
            account_type="ignitis_on",
            provider_name="Ignitis ON",
        )
        self.assertEqual(1, len(records))
        record = records[0]
        self.assertEqual(11.17, record["energy_kwh"])
        self.assertEqual(2.42, record["total_cost_eur"])
        self.assertEqual("Laivu iela 32", record["station_name"])
        self.assertEqual("LV*TEST*E1", record["connector_code"])
        self.assertTrue(record["provider_reported_energy"])
        self.assertTrue(record["provider_reported_cost"])

    def test_converts_wh_and_cents_and_skips_open_session(self) -> None:
        records = ampeco_history.parse_ampeco_transactions(
            [
                {
                    "sessionId": 9,
                    "start_date": 1_786_000_000,
                    "end_date": 1_786_003_600,
                    "energyConsumedWh": 7200,
                    "amountCents": 245,
                },
                {
                    "sessionId": 10,
                    "start_date": 1_786_000_000,
                    "energyConsumedWh": 1000,
                },
            ],
            account_id="account-2",
            account_name="IKRAUTAS",
            account_type="ikrautas",
            provider_name="IKRAUTAS",
        )
        self.assertEqual(1, len(records))
        self.assertEqual(7.2, records[0]["energy_kwh"])
        self.assertEqual(2.45, records[0]["cost_eur"])


if __name__ == "__main__":
    unittest.main()
