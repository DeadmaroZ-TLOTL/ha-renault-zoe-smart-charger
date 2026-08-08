"""Tests for public charging-station normalization helpers."""

from __future__ import annotations

import importlib.util
import html
import json
from pathlib import Path
import sys
import types
import unittest


PACKAGE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "zoe_new_extended"
)
PACKAGE_NAME = "zoe_new_extended_station_tests"
package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_PATH)]
sys.modules[PACKAGE_NAME] = package


def _load(name: str):
    module_name = f"{PACKAGE_NAME}.{name}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        PACKAGE_PATH / f"{name}.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_load("elektrum_drive_data")
elektrum_data = sys.modules[f"{PACKAGE_NAME}.elektrum_drive_data"]
stations_data = _load("stations_data")


class StationsDataTest(unittest.TestCase):
    """Verify both provider catalogs use one frontend contract."""

    def test_normalizes_elektrum_station(self) -> None:
        station = {
            "id": "station-1",
            "country": "Latvia",
            "city": "Carnikava",
            "address": "Laivu iela 32",
            "coordinates": "57.129;24.274",
            "partner": False,
            "chargingPoints": [
                {
                    "name": "LAIVU IELA",
                    "connectors": [
                        {
                            "code": "PLVCARLA32002TP2",
                            "type": "Type 2",
                            "currentType": "AC",
                            "chargingPowerType": "22kW",
                        }
                    ],
                }
            ],
            "translatable": [
                {"locale": "lv", "name": "Laivu iela", "description": "24/7"}
            ],
        }

        result = stations_data.normalize_elektrum_station(station)

        self.assertEqual("elektrum", result["provider"])
        self.assertEqual("Laivu iela", result["name"])
        self.assertEqual(22.0, result["max_power_kw"])
        self.assertEqual(1, result["connector_count"])
        self.assertEqual(57.129, result["latitude"])
        self.assertEqual("Elektrum Drive", result["operator"])

    def test_elektrum_connector_numbers_are_unique_across_charge_points(self) -> None:
        station = {
            "chargingPoints": [
                {
                    "id": "point-a",
                    "connectors": [
                        {
                            "code": "PLVTEST001TP2",
                            "sequence": 1,
                            "type": "Type 2",
                        }
                    ],
                },
                {
                    "id": "point-b",
                    "connectors": [
                        {
                            "code": "PLVTEST002TP2",
                            "sequence": 1,
                            "type": "Type 2",
                        }
                    ],
                },
            ]
        }

        connectors = elektrum_data.station_connectors(station)

        self.assertEqual([1, 2], [item["connector_number"] for item in connectors])
        self.assertEqual([1, 1], [item["connector_sequence"] for item in connectors])

    def test_elektrum_unique_catalog_sequences_are_preserved(self) -> None:
        station = {
            "chargingPoints": [
                {"connectors": [{"code": "PLVTEST002TP2", "sequence": 2}]},
                {"connectors": [{"code": "PLVTEST001TP2", "sequence": 1}]},
            ]
        }

        connectors = elektrum_data.station_connectors(station)

        self.assertEqual([2, 1], [item["connector_number"] for item in connectors])

    def test_direct_sequence_cannot_replace_station_plug_number(self) -> None:
        snapshot = {
            "data": {
                "connector": {
                    "id": "connector-a",
                    "code": "PLVTEST002TP2",
                    "sequence": 1,
                    "status": "available",
                }
            }
        }
        page = (
            '<div wire:snapshot="'
            + html.escape(json.dumps(snapshot), quote=True)
            + '"></div>'
        )

        direct = elektrum_data.parse_connector_page(page)

        self.assertEqual(1, direct["connector_sequence"])
        self.assertNotIn("connector_number", direct)

    def test_normalizes_mobilly_station_and_converts_watts(self) -> None:
        site = {
            "uid": "ev_charge/2915",
            "id": "2915",
            "name": "Test station",
            "description": "Riga",
            "type": "ev_charge",
            "location": {"type": "Point", "coordinates": [24.1, 56.95]},
            "siteDetails": {
                "connectors": [
                    {"type": "CCS", "maxPower": 150000, "count": 2},
                    {"type": "Type 2", "maxPower": 22000, "count": 1},
                ]
            },
        }

        result = stations_data.normalize_mobilly_station(site)

        self.assertEqual("mobilly", result["provider"])
        self.assertEqual(150.0, result["max_power_kw"])
        self.assertEqual(3, result["connector_count"])
        self.assertEqual(3, len(result["connectors"]))
        self.assertTrue(all(item["count"] == 1 for item in result["connectors"]))
        self.assertEqual("unknown", result["availability"])
        self.assertTrue(result["live_data_requires_mobile_session"])

    def test_extracts_mobilly_operator_from_description(self) -> None:
        result = stations_data.normalize_mobilly_station(
            {
                "id": "2",
                "type": "ev_charge",
                "name": "Example",
                "description": "(Eleport) Riga, Example street",
                "location": {"coordinates": [24.1, 56.95]},
                "siteDetails": {"connectors": []},
            }
        )

        self.assertEqual("Eleport", result["operator"])

    def test_ignores_non_ev_mobilly_sites(self) -> None:
        result = stations_data.normalize_mobilly_station(
            {
                "id": "1",
                "type": "parking",
                "location": {"coordinates": [24.1, 56.95]},
            }
        )

        self.assertIsNone(result)

    def test_emobi_uses_official_per_minute_tariff(self) -> None:
        result = stations_data.normalize_elektrum_station(
            {
                "id": "emobi-1",
                "coordinates": "56.95;24.10",
                "partner": True,
                "chargingPoints": [
                    {
                        "connectors": [
                            {
                                "code": "LV*CSD*E0001",
                                "type": "CCS",
                                "chargingPowerType": "50kW",
                            }
                        ]
                    }
                ],
                "translatable": [{"locale": "lv", "name": "e-mobi Riga"}],
            }
        )

        self.assertEqual("e-mobi", result["operator"])
        self.assertEqual(19.0, result["price_value"])
        self.assertEqual("min", result["price_unit"])
        self.assertIsNone(result["price_c_per_kwh"])
        self.assertEqual("19 c/min", result["connectors"][0]["price_formatted"])

    def test_normalizes_official_emobi_live_data(self) -> None:
        result = stations_data.normalize_emobi_station(
            {
                "geometry": {"coordinates": [24.317686, 57.078707]},
                "properties": {
                    "id": 58,
                    "uuid": "station-uuid",
                    "name": "ADAZI",
                    "companyName": "csdd",
                    "status": "Available",
                    "address": {"street": "Rigas gatve 45"},
                    "connectors": [
                        {
                            "id": 167,
                            "code": "0072E",
                            "type": "CCS",
                            "maxPowerKw": 50,
                            "currentType": "DC",
                            "status": "Available",
                            "rate": {"unit": "min", "rate": "0.19"},
                        },
                        {
                            "id": 168,
                            "code": "0071E",
                            "type": "CHAdeMO",
                            "maxPowerKw": 50,
                            "currentType": "DC",
                            "status": "Occupied",
                            "rate": {"unit": "min", "rate": "0.19"},
                        },
                    ],
                },
            }
        )

        self.assertEqual("emobi", result["provider"])
        self.assertEqual("e-mobi", result["operator"])
        self.assertEqual("available", result["availability"])
        self.assertEqual(1, result["available_connectors"])
        self.assertEqual(1, result["occupied_connectors"])
        self.assertEqual("occupied", result["connectors"][1]["status"])
        self.assertEqual("19 c/min", result["price_formatted"])
        self.assertTrue(result["connector_live_data_available"])

    def test_normalizes_elektrum_from_official_emobi_map(self) -> None:
        result = stations_data.normalize_emobi_station(
            {
                "geometry": {"coordinates": [24.1, 56.9]},
                "properties": {
                    "id": 1,
                    "companyName": "echarge",
                    "status": "Available",
                    "connectors": [
                        {
                            "id": 2,
                            "type": "CCS",
                            "status": "Available",
                            "rate": {"unit": "kwh", "rate": "0.42"},
                        }
                    ],
                },
            }
        )

        self.assertEqual("emobi_elektrum", result["provider"])
        self.assertEqual("elektrum", result["provider_group"])
        self.assertEqual("Elektrum Drive", result["operator"])
        self.assertEqual("42 c/kWh", result["price_formatted"])

    def test_ignores_unknown_operator_from_emobi_catalog(self) -> None:
        result = stations_data.normalize_emobi_station(
            {
                "geometry": {"coordinates": [24.1, 56.9]},
                "properties": {"id": 1, "companyName": "other"},
            }
        )

        self.assertIsNone(result)

    def test_merges_mobilly_live_site_counts(self) -> None:
        station = stations_data.normalize_mobilly_station(
            {
                "id": "2915",
                "type": "ev_charge",
                "name": "Test",
                "location": {"coordinates": [24.1, 56.95]},
                "siteDetails": {"connectors": []},
            }
        )

        result = stations_data.merge_mobilly_statuses(
            [station],
            {
                "statuses": [
                    {
                        "id": 2915,
                        "isActive": True,
                        "connectors": {"available": 2, "occupied": 1},
                    }
                ]
            },
        )[0]

        self.assertEqual("available", result["availability"])
        self.assertEqual(2, result["available_connectors"])
        self.assertEqual(1, result["occupied_connectors"])
        self.assertTrue(result["live_data_available"])

    def test_merges_mobilly_connector_price_and_status(self) -> None:
        station = stations_data.normalize_mobilly_station(
            {
                "id": "2915",
                "type": "ev_charge",
                "name": "Test",
                "location": {"coordinates": [24.1, 56.95]},
                "siteDetails": {
                    "connectors": [
                        {"type": "CCS", "maxPower": 50000, "count": 1}
                    ]
                },
            }
        )

        result = stations_data.merge_mobilly_station_detail(
            station,
            {
                "data": {
                    "connectors": [
                        {
                            "id": "plug-7",
                            "type": "CCS",
                            "status": "available",
                            "maxPower": 50000,
                            "tariff": {"price": 0.25, "unit": "EUR/kWh"},
                        }
                    ]
                }
            },
        )

        self.assertEqual("available", result["availability"])
        self.assertEqual(25.0, result["price_value"])
        self.assertEqual("kWh", result["price_unit"])
        self.assertEqual("plug-7", result["connectors"][0]["code"])

    def test_merges_mobilly_nested_rate_price(self) -> None:
        station = stations_data.normalize_mobilly_station(
            {
                "id": "506",
                "type": "ev_charge",
                "name": "Test",
                "location": {"coordinates": [24.1, 56.95]},
                "siteDetails": {
                    "connectors": [
                        {"type": "Type 2", "maxPower": 22000, "count": 1}
                    ]
                },
            }
        )

        result = stations_data.merge_mobilly_station_detail(
            station,
            {
                "site": {
                    "connectors": [
                        {
                            "id": 1218,
                            "type": "Type 2",
                            "status": "available",
                            "maxPower": 22000,
                            "rate": {"unit": "kwh", "rate": 0.17},
                        }
                    ]
                }
            },
        )

        self.assertEqual(17.0, result["price_value"])
        self.assertEqual("17 c/kWh", result["price_formatted"])
        self.assertEqual(17.0, result["connectors"][0]["price_c_per_kwh"])

    def test_deduplicates_same_emobi_station_from_both_catalogs(self) -> None:
        elektrum = {
            "provider": "elektrum",
            "id": "e-1",
            "operator": "e-mobi",
            "latitude": 56.95,
            "longitude": 24.1,
            "availability": "unknown",
            "price_value": 19.0,
            "connectors": [{"code": "LV*CSD*E1"}],
        }
        mobilly = {
            "provider": "mobilly",
            "id": "m-1",
            "operator": "CSDD",
            "latitude": 56.9502,
            "longitude": 24.1002,
            "availability": "available",
            "price_value": 19.0,
            "live_data_available": True,
            "connectors": [{"status": "available"}],
        }

        result = stations_data.deduplicate_stations([elektrum, mobilly])

        self.assertEqual(1, len(result))
        self.assertEqual("mobilly", result[0]["provider"])
        self.assertEqual(["elektrum", "mobilly"], result[0]["source_providers"])
        self.assertEqual(["elektrum", "mobilly"], result[0]["provider_groups"])
        self.assertEqual(2, len(result[0]["provider_offers"]))

    def test_keeps_nearby_stations_from_same_provider(self) -> None:
        first = {
            "provider": "mobilly",
            "id": "506",
            "operator": "Mobilly",
            "latitude": 56.949395,
            "longitude": 24.0889,
            "connectors": [{"code": "506-Type 2-1"}],
        }
        second = {
            "provider": "mobilly",
            "id": "1293",
            "operator": "Mobilly",
            "latitude": 56.9497,
            "longitude": 24.0891,
            "connectors": [{"code": "1293-Type 2-1"}],
        }

        result = stations_data.deduplicate_stations([first, second])

        self.assertEqual(2, len(result))

    def test_deduplicates_across_spatial_bucket_boundary(self) -> None:
        first = {
            "provider": "mobilly",
            "id": "m-1",
            "operator": "e-mobi",
            "latitude": 56.95089,
            "longitude": 24.10089,
            "connectors": [],
        }
        second = {
            "provider": "emobi",
            "id": "e-1",
            "operator": "CSDD",
            "latitude": 56.95101,
            "longitude": 24.10101,
            "connectors": [],
        }

        result = stations_data.deduplicate_stations([first, second])

        self.assertEqual(1, len(result))

    def test_deduplicates_same_provider_by_connector_code(self) -> None:
        first = {
            "provider": "emobi",
            "id": "e-1",
            "latitude": 56.95,
            "longitude": 24.1,
            "connectors": [{"code": "LV*CSD*E1"}],
        }
        second = {
            "provider": "emobi",
            "id": "e-2",
            "latitude": 57.5,
            "longitude": 25.0,
            "connectors": [{"code": "lv*csd*e1"}],
        }

        result = stations_data.deduplicate_stations([first, second])

        self.assertEqual(1, len(result))

    def test_prefers_official_emobi_connector_status(self) -> None:
        mobilly = {
            "provider": "mobilly",
            "id": "m-1",
            "operator": "e-mobi",
            "latitude": 56.95,
            "longitude": 24.1,
            "availability": "available",
            "live_data_available": True,
            "price_value": 19.0,
            "connectors": [{"code": "m-1", "status": "unknown"}],
        }
        emobi = {
            "provider": "emobi",
            "id": "58",
            "operator": "e-mobi",
            "latitude": 56.9501,
            "longitude": 24.1001,
            "availability": "available",
            "live_data_available": True,
            "connector_live_data_available": True,
            "price_value": 19.0,
            "connectors": [{"code": "0072E", "status": "available"}],
        }

        result = stations_data.deduplicate_stations([mobilly, emobi])

        self.assertEqual(1, len(result))
        self.assertEqual("emobi", result[0]["provider"])
        self.assertEqual("available", result[0]["connectors"][0]["status"])

    def test_preserves_different_prices_for_combined_provider_view(self) -> None:
        elektrum = {
            "provider": "elektrum",
            "provider_group": "elektrum",
            "id": "e-1",
            "operator": "e-mobi",
            "latitude": 56.95,
            "longitude": 24.1,
            "price_value": 23.0,
            "price_unit": "kWh",
            "price_formatted": "23 c/kWh",
            "connectors": [],
        }
        mobilly = {
            "provider": "mobilly",
            "provider_group": "mobilly",
            "id": "m-1",
            "operator": "e-mobi",
            "latitude": 56.9501,
            "longitude": 24.1001,
            "price_value": 19.0,
            "price_unit": "min",
            "price_formatted": "19 c/min",
            "connectors": [],
        }

        result = stations_data.deduplicate_stations([elektrum, mobilly])[0]

        self.assertEqual(2, len(result["provider_offers"]))
        self.assertEqual(
            ["23 c/kWh", "19 c/min"],
            [offer["price_formatted"] for offer in result["provider_offers"]],
        )

    def test_merges_same_station_when_provider_operator_names_differ(self) -> None:
        mobilly = {
            "provider": "mobilly",
            "id": "506",
            "operator": "Mobilly",
            "name": "RIGA Swedbank",
            "address": "Riga, Balasta dambis 15",
            "latitude": 56.949395,
            "longitude": 24.0889,
            "connectors": [],
        }
        elektrum = {
            "provider": "emobi_elektrum",
            "provider_group": "elektrum",
            "id": "506",
            "operator": "Elektrum Drive",
            "name": "RIGA Swedbank",
            "address": "Riga, Balasta dambis 15",
            "latitude": 56.9494,
            "longitude": 24.0889,
            "price_value": 17.0,
            "connectors": [],
        }

        result = stations_data.deduplicate_stations([mobilly, elektrum])

        self.assertEqual(1, len(result))
        self.assertEqual(["elektrum", "mobilly"], result[0]["provider_groups"])


if __name__ == "__main__":
    unittest.main()
