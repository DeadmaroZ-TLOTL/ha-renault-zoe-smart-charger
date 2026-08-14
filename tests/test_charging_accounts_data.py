"""Tests for multi-account charging transaction helpers."""

from __future__ import annotations

from datetime import UTC, datetime
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

    def test_duplicate_operator_accounts_are_merged(self) -> None:
        records = charging_data.deduplicate_account_records(
            [
                {
                    "id": "original",
                    "type": "ikrautas",
                    "email": "User@Example.com",
                    "name": "IKRAUTAS",
                },
                {
                    "id": "duplicate",
                    "type": "ikrautas",
                    "email": "user@example.com",
                    "ampeco_access_token": "new-access",
                    "ampeco_refresh_token": "new-refresh",
                },
            ]
        )

        self.assertEqual(1, len(records))
        self.assertEqual("original", records[0]["id"])
        self.assertEqual("new-access", records[0]["ampeco_access_token"])
        self.assertEqual("new-refresh", records[0]["ampeco_refresh_token"])

    def test_different_operator_accounts_remain_separate(self) -> None:
        records = charging_data.deduplicate_account_records(
            [
                {"id": "one", "type": "mobilly", "mobile_phone": "111"},
                {"id": "two", "type": "mobilly", "mobile_phone": "222"},
            ]
        )

        self.assertEqual(["one", "two"], [item["id"] for item in records])

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

    def test_elektrum_anonymous_profile_requires_agreement(self) -> None:
        state = charging_data.elektrum_profile_state(
            {"data": {"type": 0, "agreements": []}}
        )

        self.assertEqual("agreement_required", state["auth_state"])
        self.assertFalse(state["agreement_linked"])

    def test_elektrum_selected_agreement_is_linked(self) -> None:
        state = charging_data.elektrum_profile_state(
            {
                "data": {
                    "type": 3,
                    "agreements": [{"id": "one", "selected": True}],
                }
            }
        )

        self.assertEqual("agreement_linked", state["auth_state"])
        self.assertTrue(state["agreement_linked"])

    def test_anonymous_token_cannot_replace_linked_profile(self) -> None:
        self.assertFalse(
            charging_data.elektrum_token_can_replace(
                {"data": {"type": 3, "agreements": [{"selected": True}]}},
                {"data": {"type": 0, "agreements": []}},
            )
        )

    def test_linked_token_can_replace_linked_profile(self) -> None:
        self.assertTrue(
            charging_data.elektrum_token_can_replace(
                {"data": {"type": 3, "agreements": [{"selected": True}]}},
                {"data": {"type": 3, "agreements": [{"selected": True}]}},
            )
        )

    def test_saved_agreement_rejects_anonymous_refresh(self) -> None:
        self.assertFalse(
            charging_data.elektrum_token_can_replace(
                None,
                {"data": {"type": 0, "agreements": []}},
                saved_agreement=True,
            )
        )

    def test_elektrum_month_keys_cover_calendar_history(self) -> None:
        months = charging_data.elektrum_month_keys(
            datetime(2026, 8, 4, 12, tzinfo=UTC),
            history_days=400,
        )

        self.assertEqual("2026-08", months[0])
        self.assertEqual("2025-06", months[-1])
        self.assertEqual(15, len(months))

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

    def test_exact_provider_transaction_combines_renault_split_rows(self) -> None:
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

        self.assertEqual(1, len(matched))
        self.assertAlmostEqual(23.44, matched[0]["grid_energy_kwh"], places=3)
        self.assertAlmostEqual(5.39, matched[0]["total_cost_eur"], places=4)
        self.assertEqual("elektrum_drive_app", matched[0]["price_source"])
        self.assertEqual(2, matched[0]["provider_split_session_count"])
        self.assertTrue(matched[0]["provider_combined_session"])
        self.assertEqual(2, len(matched[0]["renault_session_fragments"]))

    def test_real_elektrum_charge_combines_both_renault_fragments(self) -> None:
        transaction = {
            "transaction_id": "elektrum-2026-08-03",
            "source_account_type": "elektrum_drive",
            "account_id": "ed-1",
            "account_name": "Main Elektrum",
            "provider": "Elektrum Drive",
            "station_name": "PLVCARLA32002TP2",
            "station_address": "Laivu iela 32, Carnikava",
            "start": "2026-08-03T10:29:00+00:00",
            "end": "2026-08-03T12:31:00+00:00",
            "duration_minutes": 122,
            "energy_kwh": 26.366,
            "total_cost_eur": 6.06,
            "price_source": "elektrum_drive_app",
            "provider_reported_cost": True,
            "provider_reported_energy": True,
        }
        sessions = [
            {
                "start": "2026-08-03T10:29:00+00:00",
                "end": "2026-08-03T10:35:00+00:00",
                "start_soc": 57,
                "end_soc": 61,
                "estimated_battery_energy_kwh": 2.08,
                "status": "ok",
            },
            {
                "start": "2026-08-03T10:51:00+00:00",
                "end": "2026-08-03T12:31:00+00:00",
                "start_soc": 61,
                "end_soc": 100,
                "estimated_battery_energy_kwh": 20.28,
                "status": "ok",
            },
        ]

        matched = charging_data.apply_provider_transactions(
            sessions, [transaction]
        )

        self.assertEqual(1, len(matched))
        self.assertEqual(57.0, matched[0]["start_soc"])
        self.assertEqual(100.0, matched[0]["end_soc"])
        self.assertEqual(26.366, matched[0]["grid_energy_kwh"])
        self.assertEqual(6.06, matched[0]["total_cost_eur"])
        self.assertAlmostEqual(
            22.984,
            matched[0]["total_rate_c_per_kwh"],
            places=3,
        )
        self.assertEqual(2, matched[0]["provider_split_session_count"])

    def test_stop_restart_rows_are_one_physical_charge(self) -> None:
        sessions = [
            {
                "start": "2026-08-04T09:45:00+00:00",
                "end": "2026-08-04T10:01:00+00:00",
                "start_soc": 83,
                "end_soc": 93,
                "duration_min": 15,
                "estimated_battery_energy_kwh": 5.2,
                "grid_energy_kwh": 5.33,
                "total_cost_eur": 1.08,
                "station_name": "Laivu iela 32",
                "price_source": "elektrum_drive",
            },
            {
                "start": "2026-08-04T10:12:00+00:00",
                "end": "2026-08-04T10:16:00+00:00",
                "start_soc": 93,
                "end_soc": 96,
                "duration_min": 4,
                "estimated_battery_energy_kwh": 1.56,
                "grid_energy_kwh": 1.5,
                "total_cost_eur": 0.34,
                "station_name": "Laivu iela 32",
                "price_source": "elektrum_drive",
            },
            {
                "start": "2026-08-04T10:27:00+00:00",
                "end": "2026-08-04T10:31:00+00:00",
                "start_soc": 96,
                "end_soc": 98,
                "duration_min": 3,
                "estimated_battery_energy_kwh": 1.04,
                "grid_energy_kwh": 1.17,
                "total_cost_eur": 0.27,
                "station_name": "Laivu iela 32",
                "price_source": "elektrum_drive",
            },
        ]

        combined = charging_data.combine_charge_fragments(sessions)

        self.assertEqual(1, len(combined))
        self.assertEqual(83.0, combined[0]["start_soc"])
        self.assertEqual(98.0, combined[0]["end_soc"])
        self.assertEqual(46, combined[0]["duration_min"])
        self.assertEqual(22, combined[0]["active_duration_min"])
        self.assertEqual(8.0, combined[0]["grid_energy_kwh"])
        self.assertEqual(1.69, combined[0]["total_cost_eur"])
        self.assertEqual(3, combined[0]["combined_fragment_count"])

    def test_nearby_different_stations_are_not_combined(self) -> None:
        first = {
            "start": "2026-08-04T09:00:00+00:00",
            "end": "2026-08-04T09:10:00+00:00",
            "start_soc": 40,
            "end_soc": 45,
            "station_name": "Station A",
        }
        second = {
            "start": "2026-08-04T09:20:00+00:00",
            "end": "2026-08-04T09:30:00+00:00",
            "start_soc": 45,
            "end_soc": 50,
            "station_name": "Station B",
        }

        combined = charging_data.combine_charge_fragments([first, second])

        self.assertEqual(2, len(combined))

    def test_point_in_time_mobilly_transaction_uses_renault_end(self) -> None:
        sessions = [
            {
                "start": "2026-08-07T16:12:25+00:00",
                "end": "2026-08-07T16:29:18+00:00",
                "start_soc": 36,
                "end_soc": 60,
                "estimated_battery_energy_kwh": 12.48,
            }
        ]
        transactions = [
            {
                "transaction_id": "mobilly-second-account",
                "account_id": "mobilly-2",
                "account_name": "Second Mobilly",
                "provider": "Mobilly",
                "start": "2026-08-07T16:12:25+00:00",
                "end": "2026-08-07T16:12:25+00:00",
                "end_inferred": True,
                "total_cost_eur": 2.5,
                "price_source": "mobilly",
                "provider_reported_cost": True,
                "provider_reported_energy": False,
            }
        ]

        matched = charging_data.apply_provider_transactions(
            sessions,
            transactions,
        )

        self.assertEqual(1, len(matched))
        self.assertEqual("2026-08-07T16:29:18+00:00", matched[0]["end"])
        self.assertEqual(2.5, matched[0]["total_cost_eur"])
        self.assertEqual("mobilly", matched[0]["price_source"])

    def test_ignitis_app_wins_over_matching_mobilly_row(self) -> None:
        operator = {
            "transaction_id": "ignitis-42",
            "source_account_type": "ignitis_on",
            "provider": "Ignitis ON",
            "operator": "Ignitis ON",
            "start": "2026-08-08T10:00:00+00:00",
            "end": "2026-08-08T10:30:00+00:00",
            "energy_kwh": 20.1,
            "total_cost_eur": 6.03,
            "price_source": "ignitis_on_app",
        }
        reseller = {
            "transaction_id": "mobilly-99",
            "source_account_type": "mobilly",
            "provider": "Ignitis ON via Mobilly",
            "operator": "Mobilly",
            "start": "2026-08-08T10:01:00+00:00",
            "end": "2026-08-08T10:31:00+00:00",
            "energy_kwh": 20.0,
            "total_cost_eur": 6.2,
            "price_source": "mobilly",
        }

        merged = charging_data.merge_account_transactions([reseller], [operator])

        self.assertEqual(1, len(merged))
        self.assertEqual("ignitis_on_app", merged[0]["price_source"])
        self.assertEqual(6.03, merged[0]["total_cost_eur"])
        self.assertEqual(1, len(merged[0]["alternate_sources"]))


if __name__ == "__main__":
    unittest.main()
