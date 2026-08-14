"""Tests for public Ignitis ON and IKRAUTAS station normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "ampeco_stations_data.py"
)
SPEC = importlib.util.spec_from_file_location("ampeco_stations_data_tests", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ampeco_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ampeco_data)


class AmpecoStationsDataTest(unittest.TestCase):
    """Verify public AMPECO detail is preserved for the station map."""

    def test_normalizes_connectors_status_and_tariff(self) -> None:
        locations = [
            {
                "id": 142,
                "name": "Vilniaus g. 2B",
                "address": "Vilniaus g. 2B, Kretinga, Lithuania",
                "location": "55.8909556,21.2420518",
                "timezone": "Europe/Vilnius",
                "updatedAt": "2026-08-13 08:22:03.000",
                "zones": [
                    {
                        "evses": [
                            {
                                "id": "1080",
                                "identifier": "8008",
                                "networkId": "1",
                                "maxPower": 22000,
                                "currentType": "ac",
                                "status": "available",
                                "isAvailable": True,
                                "tariffId": "80",
                                "connectors": [
                                    {
                                        "id": "680",
                                        "name": "Type 2",
                                        "format": "socket",
                                    }
                                ],
                            },
                            {
                                "id": "1081",
                                "emi3Identifier": "LT*IKR*E0001",
                                "networkId": "2",
                                "maxPower": 50000,
                                "currentType": "dc",
                                "status": "charging",
                                "tariffId": "80",
                                "connectors": [{"id": "681", "name": "CCS"}],
                            },
                        ]
                    }
                ],
            }
        ]
        tariffs = [
            {
                "id": "80",
                "currencyCode": "EUR",
                "priceForEnergy": 0.3,
                "connectionFee": 0.3,
                "minPrice": 0.5,
                "arePricesTaxInclusive": True,
            }
        ]

        result = ampeco_data.normalize_ampeco_catalog(
            locations,
            tariffs,
            provider="ikrautas",
            provider_group="ikrautas",
            operator="IKRAUTAS",
        )[0]

        self.assertEqual("ikrautas", result["provider"])
        self.assertEqual("Lithuania", result["country"])
        self.assertEqual(2, result["connector_count"])
        self.assertEqual(50.0, result["max_power_kw"])
        self.assertEqual("available", result["availability"])
        self.assertEqual(1, result["available_connectors"])
        self.assertEqual(1, result["occupied_connectors"])
        self.assertEqual(30.0, result["price_c_per_kwh"])
        self.assertEqual("ikrautas:evse:1080", result["connectors"][0]["code"])
        self.assertEqual("LT*IKR*E0001", result["connectors"][1]["code"])
        self.assertEqual(2, result["connectors"][1]["connector_number"])
        self.assertIn("EUR 0.30/connection", result["price_formatted"])

    def test_rejects_location_without_coordinates(self) -> None:
        result = ampeco_data.normalize_ampeco_station(
            {"id": 1, "name": "Missing coordinates"},
            {},
            provider="ignitis_on",
            provider_group="ignitis",
            operator="Ignitis ON",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
