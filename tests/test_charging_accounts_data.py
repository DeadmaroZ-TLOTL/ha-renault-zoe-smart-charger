"""Tests for multi-account charging transaction helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "charging_accounts_data.py"
)
SPEC = importlib.util.spec_from_file_location("charging_accounts_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
charging_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(charging_data)


ELEKTRUM_PAYLOAD = {
    "data": [
        {
            "id": "elektrum-1",
            "amount": 539,
            "createdAt": 1720090000,
            "status": 2,
            "type": 2,
            "invoiceAvailable": True,
            "item": {
                "duration": 100,
                "startedAt": 1720080000,
                "endedAt": 1720086000,
                "energyUsed": 23440,
                "stationAddress": "Laivu iela 32, Carnikava",
                "stationName": "PLVCARLA32002TP2",
                "tariffChargingPriceFull": 23.0,
                "tariffChargingUnit": 2,
                "tariffConnectionPriceFull": 0.0,
                "tariffConnectionUnit": 0,
            },
        }
    ]
}


class ChargingAccountsDataTest(unittest.TestCase):
    """Verify exact provider data and cross-account de-duplication."""

    def test_parses_elektrum_units(self) -> None:
        records = charging_data.parse_elektrum_transactions(
            ELEKTRUM_PAYLOAD,
            account_id="ed-1",
            account_name="Main Elektrum",
        )

        self.assertEqual(1, len(records))
        self.assertEqual(23.44, records[0]["energy_kwh"])
        self.assertEqual(5.39, records[0]["total_cost_eur"])
        self.assertEqual("elektrum_drive_app", records[0]["price_source"])
        self.assertEqual("success", records[0]["transaction_status"])

    def test_elektrum_app_wins_over_matching_mobilly_row(self) -> None:
        elektrum = charging_data.parse_elektrum_transactions(
            ELEKTRUM_PAYLOAD,
            account_id="ed-1",
            account_name="Main Elektrum",
        )
        mobilly = [
            {
                "transaction_id": "mobilly-9",
                "source_account_type": "mobilly",
                "account_id": "mob-1",
                "account_name": "Mobilly invoice",
                "provider": "Latvenergo AS",
                "start": elektrum[0]["start"],
                "end": elektrum[0]["end"],
                "energy_kwh": 23.4,
                "total_cost_eur": 5.5,
                "price_source": "mobilly",
                "elektrum_transaction": True,
                "provider_reported_cost": True,
                "provider_reported_energy": True,
            }
        ]

        merged = charging_data.merge_account_transactions(mobilly, elektrum)

        self.assertEqual(1, len(merged))
        self.assertEqual("elektrum_drive_app", merged[0]["price_source"])
        self.assertEqual(5.39, merged[0]["total_cost_eur"])
        self.assertEqual(
            "mobilly-9",
            merged[0]["alternate_sources"][0]["transaction_id"],
        )

    def test_same_transaction_from_two_accounts_is_counted_once(self) -> None:
        first = charging_data.parse_elektrum_transactions(
            ELEKTRUM_PAYLOAD,
            account_id="ed-1",
            account_name="First",
        )
        second = charging_data.parse_elektrum_transactions(
            ELEKTRUM_PAYLOAD,
            account_id="ed-2",
            account_name="Second",
        )

        merged = charging_data.merge_account_transactions(first, second)

        self.assertEqual(1, len(merged))
        self.assertEqual("ed-2", merged[0]["alternate_sources"][0]["account_id"])

    def test_equal_account_local_ids_do_not_hide_different_charges(self) -> None:
        first = {
            "transaction_id": "123",
            "source_account_type": "mobilly",
            "account_id": "mobilly-a",
            "provider": "Other network",
            "start": "2026-08-01T08:00:00+00:00",
            "end": "2026-08-01T09:00:00+00:00",
            "energy_kwh": 10.0,
            "total_cost_eur": 2.0,
        }
        second = {
            **first,
            "account_id": "mobilly-b",
            "start": "2026-08-02T08:00:00+00:00",
            "end": "2026-08-02T09:00:00+00:00",
        }

        merged = charging_data.merge_account_transactions([first], [second])

        self.assertEqual(2, len(merged))

    def test_exact_totals_are_allocated_across_renault_split_rows(self) -> None:
        transaction = charging_data.parse_elektrum_transactions(
            ELEKTRUM_PAYLOAD,
            account_id="ed-1",
            account_name="Main Elektrum",
        )[0]
        sessions = [
            {
                "start": transaction["start"],
                "end": "2024-07-04T08:40:00+00:00",
                "estimated_battery_energy_kwh": 5.2,
            },
            {
                "start": "2024-07-04T08:45:00+00:00",
                "end": transaction["end"],
                "estimated_battery_energy_kwh": 15.6,
            },
        ]

        matched = charging_data.apply_provider_transactions(
            sessions, [transaction]
        )

        self.assertAlmostEqual(
            23.44,
            sum(item["grid_energy_kwh"] for item in matched),
            places=3,
        )
        self.assertAlmostEqual(
            5.39,
            sum(item["total_cost_eur"] for item in matched),
            places=4,
        )
        self.assertTrue(
            all(item["price_source"] == "elektrum_drive_app" for item in matched)
        )


if __name__ == "__main__":
    unittest.main()
