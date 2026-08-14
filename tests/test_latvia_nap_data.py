"""Tests for Latvia National Access Point DATEX II normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "latvia_nap_data.py"
)
SPEC = importlib.util.spec_from_file_location("latvia_nap_data_tests", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
nap_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nap_data)

INFRASTRUCTURE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<payload xmlns:egi="http://datex2.eu/schema/3/energyInfrastructure"
         xmlns:fac="http://datex2.eu/schema/3/facilities"
         xmlns:loc="http://datex2.eu/schema/3/locationReferencing">
  <egi:energyInfrastructureTable>
    <egi:energyInfrastructureSite id="site-1" version="1">
      <fac:name><fac:values><fac:value lang="en">Test station</fac:value></fac:values></fac:name>
      <fac:locationReference>
        <loc:pointByCoordinates><loc:pointCoordinates>
          <loc:latitude>56.95</loc:latitude><loc:longitude>24.10</loc:longitude>
        </loc:pointCoordinates></loc:pointByCoordinates>
        <loc:_pointLocationExtension><fac:facilityLocation><fac:address>
          <fac:postcode>LV-1001</fac:postcode><fac:city>Riga</fac:city>
          <fac:countryCode>LV</fac:countryCode>
          <fac:addressLine order="0"><fac:type>street</fac:type><fac:text>Main iela 1</fac:text></fac:addressLine>
        </fac:address></fac:facilityLocation></loc:_pointLocationExtension>
      </fac:locationReference>
      <fac:operator id="operator-1" version="1">
        <fac:name><fac:values><fac:value lang="en">Test operator</fac:value></fac:values></fac:name>
      </fac:operator>
      <egi:energyInfrastructureStation id="station-1" version="1">
        <egi:refillPoint id="point-1" version="1">
          <fac:externalIdentifier>LV*TEST*E001</fac:externalIdentifier>
          <egi:connector><egi:connectorType>iec62196T2COMBO</egi:connectorType><egi:chargingMode>mode4DC</egi:chargingMode><egi:maxPowerAtSocket>150000</egi:maxPowerAtSocket></egi:connector>
          <egi:connector><egi:connectorType>chademo</egi:connectorType><egi:chargingMode>mode4DC</egi:chargingMode><egi:maxPowerAtSocket>50000</egi:maxPowerAtSocket></egi:connector>
        </egi:refillPoint>
      </egi:energyInfrastructureStation>
    </egi:energyInfrastructureSite>
  </egi:energyInfrastructureTable>
</payload>"""

STATUS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<payload xmlns:egi="http://datex2.eu/schema/3/energyInfrastructure"
         xmlns:fac="http://datex2.eu/schema/3/facilities">
  <egi:energyInfrastructureSiteStatus>
    <fac:reference id="site-1" version="1" />
    <fac:lastUpdated>2026-08-13T10:15:00+00:00</fac:lastUpdated>
    <egi:energyInfrastructureStationStatus>
      <fac:reference id="point-1" version="1" />
      <fac:lastUpdated>2026-08-13T10:14:00+00:00</fac:lastUpdated>
      <fac:newRates id="1" version="1">
        <fac:rateLineCollection><fac:rateLine sequence="1">
          <fac:rateLineType>perUnit</fac:rateLineType><fac:value>0.36</fac:value>
          <fac:rateLineTax><fac:taxRate>21</fac:taxRate><fac:taxIncluded>false</fac:taxIncluded></fac:rateLineTax>
        </fac:rateLine></fac:rateLineCollection>
      </fac:newRates>
      <egi:refillPointStatus>
        <fac:reference id="LV*TEST*E001" version="1" />
        <egi:status>charging</egi:status>
      </egi:refillPointStatus>
    </egi:energyInfrastructureStationStatus>
  </egi:energyInfrastructureSiteStatus>
</payload>"""


class LatviaNapDataTest(unittest.TestCase):
    """Verify DATEX parsing, tariff tax handling, and URL validation."""

    def test_parses_station_status_connectors_and_gross_price(self) -> None:
        stations = nap_data.parse_latvia_nap_catalog(
            INFRASTRUCTURE_XML,
            STATUS_XML,
        )

        self.assertEqual(1, len(stations))
        station = stations[0]
        self.assertEqual("latvia_nap", station["provider"])
        self.assertEqual("nap", station["provider_group"])
        self.assertEqual("Test station", station["name"])
        self.assertEqual("Test operator", station["operator"])
        self.assertEqual("Main iela 1", station["address"])
        self.assertEqual("occupied", station["availability"])
        self.assertEqual(150.0, station["max_power_kw"])
        self.assertEqual(43.56, station["price_c_per_kwh"])
        self.assertEqual("43.56 c/kWh", station["price_formatted"])
        self.assertEqual(2, len(station["connectors"]))
        self.assertEqual("CCS (Type 2)", station["connectors"][0]["connector_type"])
        self.assertEqual("CHAdeMO", station["connectors"][1]["connector_type"])
        self.assertTrue(station["connector_live_data_available"])

    def test_static_data_without_status_is_not_marked_live(self) -> None:
        stations = nap_data.parse_latvia_nap_catalog(
            INFRASTRUCTURE_XML,
            b"<payload />",
        )

        self.assertFalse(stations[0]["live_data_available"])
        self.assertEqual("unknown", stations[0]["availability"])
        self.assertIsNone(stations[0]["available_connectors"])

    def test_zero_rate_is_treated_as_unknown_not_free(self) -> None:
        status_xml = STATUS_XML.replace(
            b"<fac:value>0.36</fac:value>",
            b"<fac:value>0</fac:value>",
        )

        station = nap_data.parse_latvia_nap_catalog(
            INFRASTRUCTURE_XML,
            status_xml,
        )[0]

        self.assertNotIn("price_value", station)
        self.assertNotIn("price_value", station["connectors"][0])

    def test_multiple_rates_are_shown_as_a_range(self) -> None:
        second_rate = b"""
        <fac:rateLine sequence="2">
          <fac:rateLineType>perUnit</fac:rateLineType><fac:value>0.39</fac:value>
          <fac:rateLineTax><fac:taxRate>21</fac:taxRate><fac:taxIncluded>false</fac:taxIncluded></fac:rateLineTax>
        </fac:rateLine>"""
        status_xml = STATUS_XML.replace(
            b"</fac:rateLine></fac:rateLineCollection>",
            b"</fac:rateLine>" + second_rate + b"</fac:rateLineCollection>",
        )

        station = nap_data.parse_latvia_nap_catalog(
            INFRASTRUCTURE_XML,
            status_xml,
        )[0]

        self.assertEqual([43.56, 47.19], station["price_options_c_per_kwh"])
        self.assertEqual("43.56-47.19 c/kWh", station["price_formatted"])

    def test_selects_newest_allowed_download_url(self) -> None:
        metadata = {
            "field_download_url": [
                {
                    "field_file": [
                        {
                            "fid": "10",
                            "url": "https://www.transportdata.gov.lv/npp-test/old.xml",
                        },
                        {
                            "fid": "11",
                            "url": "https://www.transportdata.gov.lv/npp-test/current.xml",
                        },
                    ]
                }
            ]
        }

        self.assertEqual(
            "https://www.transportdata.gov.lv/npp-test/current.xml",
            nap_data.current_download_url(metadata),
        )

    def test_rejects_unexpected_download_host(self) -> None:
        metadata = {
            "field_download_url": [
                {
                    "field_file": [
                        {"fid": "1", "url": "https://example.com/feed.xml"}
                    ]
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "unexpected file URL"):
            nap_data.current_download_url(metadata)


if __name__ == "__main__":
    unittest.main()
