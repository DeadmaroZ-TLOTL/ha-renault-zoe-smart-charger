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

    def test_normalizes_live_ampeco_session_shape_and_location(self) -> None:
        raw = {
            "address": "Vilniaus Ave 7, Druskininkai 66119, Lithuania",
            "evse": {"identifier": "5003", "label": None},
            "note": "Vilniaus Ave 7, Druskininkai 66119, Lithuania",
            "receiptUrl": "https://example.test/receipt/103093",
            "session": {
                "id": "103093",
                "startedAt": "2026-08-10T17:06:10+00:00",
                "stoppedAt": "2026-08-10T19:36:05+00:00",
                "energy": 46460,
                "totalAmount": 21.21,
                "duration": 8995,
                "totalDuration": 8995,
                "locationId": 21,
                "evseId": "5003",
                "status": "finished",
                "currency": {"code": "EUR"},
            },
            "type": "public",
        }
        locations = ampeco_history.ampeco_location_lookup(
            {
                "locations": [
                    {
                        "id": 21,
                        "name": "Druskininkai charging site",
                        "address": "Vilniaus Ave 7, Druskininkai",
                    }
                ]
            }
        )

        records = ampeco_history.parse_ampeco_transactions(
            [raw],
            account_id="account-live",
            account_name="IKRAUTAS",
            account_type="ikrautas",
            provider_name="IKRAUTAS",
            locations=locations,
        )

        self.assertEqual(["21"], ampeco_history.ampeco_history_location_ids([raw]))
        self.assertEqual(1, len(records))
        record = records[0]
        self.assertEqual("21", record["station_id"])
        self.assertEqual("Druskininkai charging site", record["station_name"])
        self.assertEqual("5003", record["connector_code"])
        self.assertEqual(150, record["duration_minutes"])
        self.assertEqual(46.46, record["energy_kwh"])
        self.assertEqual(21.21, record["cost_eur"])
        self.assertEqual("EUR", record["currency"])
        self.assertEqual(
            "https://example.test/receipt/103093", record["receipt_url"]
        )


if __name__ == "__main__":
    unittest.main()
