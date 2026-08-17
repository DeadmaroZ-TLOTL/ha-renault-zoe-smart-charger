"""Tests for Mobilly charging data helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "mobilly_data.py"
)
SPEC = importlib.util.spec_from_file_location("mobilly_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
mobilly_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mobilly_data)


DIRECT_PAGE = """
<table><tr>
<th>Id</th><th>Number</th><th>Auto</th><th>RFID karte</th>
<th>Pakalpojumu sniedzējs</th><th>Darījuma laiks</th>
<th>Pakalpojums</th><th>Laiks</th><th>Apjoms</th><th>Cena EUR</th>
</tr><tr>
<td>190356054</td><td>37100000000</td><td>BE:10056E</td><td></td>
<td>ADD Energy SIA (LV)</td><td>2025-01-04</td>
<td>Elektroauto uzlāde; 30.8kWh</td><td>14:17 - 15:50</td>
<td>30.770 kWh</td><td>5.23</td>
</tr><tr>
<td>190356055</td><td>37100000000</td><td></td><td></td>
<td>Latvenergo AS</td><td>2025-01-05</td>
<td>Elektroauto uzlāde Elektrum Drive stacijā; 5.0kWh</td>
<td>10:00 - 10:20</td><td>5.000 kWh</td><td>1.15</td>
</tr></table>
"""

INVOICE_PAGE = """
<table><tr>
<th>Id</th><th>Number</th><th>Auto</th><th>Pakalpojumu sniedzējs</th>
<th>Darījuma laiks</th><th>Pakalpojums</th><th>Apjoms</th>
<th>PVN summa EUR</th><th>Cena EUR</th>
</tr><tr>
<td>19887168</td><td>37100000000</td><td>BE:</td><td>Plugfree OÜ (EE)</td>
<td>2025-08-04 11:48 - 13:25</td><td>Elektroauto uzlāde Plugfree tīklā EE</td>
<td>525 h 48 min</td><td>0.00</td><td>10.73</td>
</tr><tr>
<td>19887169</td><td>37100000000</td><td>BE:</td><td>Mobilly, SIA</td>
<td>2025-08-04 11:48 - 13:25</td>
<td>Komisija lādējot auto Plugfree EE stacijā pie mobilā rēķina</td>
<td>1 gab.</td><td>0.11</td><td>0.65</td>
</tr><tr>
<td>21223464</td><td>37100000000</td><td>BE:</td><td>Latvenergo AS</td>
<td>2026-02-19 08:36 - 08:45</td><td>Elektroauto uzlāde Elektrum Drive stacijā</td>
<td>45 h 00 min</td><td>0.18</td><td>1.02</td>
</tr><tr><td>Kopā apmaksāts:</td><td></td><td></td><td></td><td></td>
<td></td><td></td><td>0.29</td><td>12.40</td></tr></table>
"""


class MobillyDataTest(unittest.TestCase):
    """Verify both statements merge without duplicating Elektrum sessions."""

    def test_rejects_elektrum_operator(self) -> None:
        record = {
            "id": "PLVCARLA32002TP2",
            "operator": {"name": "Elektrum Drive"},
            "station": {"name": "Laivu iela 32"},
        }

        self.assertTrue(mobilly_data.is_elektrum_station(record))

    def test_rejects_latvenergo_brand(self) -> None:
        record = {
            "site": {
                "title": "Carnikava",
                "provider": {"brand": "AS Latvenergo"},
            }
        }

        self.assertTrue(mobilly_data.is_elektrum_station(record))

    def test_keeps_other_mobilly_networks(self) -> None:
        records = [
            {"id": "ene-1", "network": "Enefit Volt"},
            {"id": "el-1", "provider": "Elektrum Drive"},
            {"id": "ign-1", "operator": {"name": "Ignitis ON"}},
        ]

        self.assertEqual(
            ["ene-1", "ign-1"],
            [item["id"] for item in mobilly_data.without_elektrum(records)],
        )

    def test_does_not_reject_unrelated_text_fields(self) -> None:
        record = {
            "operator": "Eleport",
            "note": "Imported after an Elektrum session",
        }

        self.assertFalse(mobilly_data.is_elektrum_station(record))

    def test_parses_direct_energy_and_cost(self) -> None:
        records = mobilly_data.parse_transactions_page(
            DIRECT_PAGE, source_page="payments"
        )

        self.assertEqual(2, len(records))
        self.assertEqual(30.77, records[0]["energy_kwh"])
        self.assertEqual(5.23, records[0]["cost_eur"])
        self.assertEqual("2025-01-04T12:17:00+00:00", records[0]["start"])

    def test_merges_invoice_commission_and_keeps_real_elektrum_rows(self) -> None:
        direct = mobilly_data.parse_transactions_page(
            DIRECT_PAGE, source_page="payments"
        )
        invoice = mobilly_data.parse_transactions_page(
            INVOICE_PAGE, source_page="payments_mobile"
        )

        merged = mobilly_data.merge_transactions(direct, invoice)

        self.assertEqual(4, len(merged))
        plugfree = next(item for item in merged if item["provider"].startswith("Plugfree"))
        self.assertEqual(0.65, plugfree["commission_cost_eur"])
        self.assertEqual(11.38, plugfree["total_cost_eur"])
        elektrum = [item for item in merged if item["elektrum_transaction"]]
        self.assertEqual(2, len(elektrum))
        self.assertTrue(all(item["provider_reported_cost"] for item in elektrum))

    def test_parses_app_ev_transaction_cost_in_cents(self) -> None:
        payload = {
            "data": {
                "transactions": [
                    {
                        "id": "mobile-1",
                        "type": "EV_CHARGING",
                        "serviceName": "EV charging",
                        "serviceProviderName": "Mobilly network",
                        "comment": "11.8kWh",
                        "cost": 76,
                        "startTime": "2026-08-07T16:12:25Z",
                        "status": "completed",
                    },
                    {
                        "id": "parking-1",
                        "type": "PARKING",
                        "cost": 100,
                        "startTime": "2026-08-07T15:00:00Z",
                    },
                ]
            }
        }

        records = mobilly_data.parse_app_transactions(payload)

        self.assertEqual(1, len(records))
        self.assertEqual(0.76, records[0]["cost_eur"])
        self.assertEqual(11.8, records[0]["energy_kwh"])
        self.assertIsNone(records[0]["station_name"])
        self.assertEqual(records[0]["start"], records[0]["end"])
        self.assertTrue(records[0]["end_inferred"])

    def test_app_session_enriches_history_interval_and_energy(self) -> None:
        history = mobilly_data.parse_app_transactions(
            {
                "transactions": [
                    {
                        "id": "mobile-2",
                        "type": "EV_CHARGING",
                        "serviceProviderName": "Mobilly",
                        "cost": 250,
                        "startTime": "2026-08-07T16:12:25Z",
                    }
                ]
            }
        )
        sessions = mobilly_data.parse_app_charge_sessions(
            {
                "data": {
                    "sessions": [
                        {
                            "transactionId": "mobile-2",
                            "providerName": "Mobilly",
                            "stationName": "Charging station",
                            "startedAt": "2026-08-07T16:12:25Z",
                            "endedAt": "2026-08-07T16:29:18Z",
                            "energyKwh": 13.17,
                        }
                    ]
                }
            }
        )

        merged = mobilly_data.merge_app_transactions(history, sessions)

        self.assertEqual(1, len(merged))
        self.assertEqual("2026-08-07T16:29:18+00:00", merged[0]["end"])
        self.assertFalse(merged[0]["end_inferred"])
        self.assertEqual(13.17, merged[0]["energy_kwh"])
        self.assertEqual(2.5, merged[0]["total_cost_eur"])

    def test_partial_refresh_keeps_app_energy_without_doubling_commission(self) -> None:
        fresh = {
            "account_id": "mobilly-1",
            "transaction_id": "web-42",
            "source_page": "payments_mobile",
            "source_pages": ["payments", "payments_mobile"],
            "provider": "Eleport SIA",
            "start": "2026-08-07T16:12:00+00:00",
            "end": "2026-08-07T16:29:00+00:00",
            "energy_kwh": None,
            "cost_eur": 5.19,
            "commission_cost_eur": 0.2,
            "total_cost_eur": 5.39,
        }
        cached = {
            "account_id": "mobilly-1",
            "transaction_id": "app-42",
            "session_id": "session-42",
            "source_page": "mobilly_app_charge_sessions",
            "provider": "Eleport SIA",
            "station_name": "t/c Saga",
            "connector_code": "LV*ELE*E42",
            "start": "2026-08-07T16:12:00+00:00",
            "end": "2026-08-07T16:29:00+00:00",
            "energy_kwh": 11.8,
            "cost_eur": 5.19,
            "commission_cost_eur": 0.0,
            "total_cost_eur": 5.19,
        }
        older = {
            **cached,
            "transaction_id": "app-older",
            "start": "2026-07-10T12:00:00+00:00",
            "end": "2026-07-10T12:20:00+00:00",
        }

        result = mobilly_data.merge_cached_app_history(
            [fresh],
            [cached, older],
        )

        self.assertEqual(2, len(result))
        merged = next(item for item in result if item["transaction_id"] == "web-42")
        self.assertEqual(11.8, merged["energy_kwh"])
        self.assertEqual("t/c Saga", merged["station_name"])
        self.assertEqual(0.2, merged["commission_cost_eur"])
        self.assertEqual(5.39, merged["total_cost_eur"])
        self.assertEqual(45.678, merged["total_rate_c_per_kwh"])


if __name__ == "__main__":
    unittest.main()
