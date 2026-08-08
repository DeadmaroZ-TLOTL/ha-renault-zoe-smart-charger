"""Tests for Zoe II charge start and schedule-based stop commands."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import importlib.util
from pathlib import Path
import sys
import types
import unittest


PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "zoe_new_extended"
PACKAGE_NAME = "zoe_new_extended_charge_control_tests"
package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_PATH)]
sys.modules[PACKAGE_NAME] = package


class RenaultException(Exception):
    """Stub Renault API exception."""


class ChargeState(Enum):
    """Subset used by the command confirmation loop."""

    CHARGE_IN_PROGRESS = 1
    NOT_IN_CHARGE = 0


@dataclass
class EndpointDefinition:
    """Stub Renault endpoint definition."""

    endpoint: str
    mode: str = "default"


class KamereonVehicleChargingStartActionData:
    """Stub action result."""


def _install_import_stubs() -> None:
    renault_api = types.ModuleType("renault_api")
    renault_exceptions = types.ModuleType("renault_api.exceptions")
    renault_exceptions.RenaultException = RenaultException
    kamereon = types.ModuleType("renault_api.kamereon")
    schemas = types.ModuleType("renault_api.kamereon.schemas")
    schemas.KamereonVehicleChargingStartActionDataSchema = object
    schemas.KamereonVehicleChargeScheduleActionDataSchema = object
    enums = types.ModuleType("renault_api.kamereon.enums")
    enums.ChargeState = ChargeState
    models = types.ModuleType("renault_api.kamereon.models")
    models.EndpointDefinition = EndpointDefinition
    models.KamereonVehicleChargingStartActionData = (
        KamereonVehicleChargingStartActionData
    )
    kamereon.schemas = schemas

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntryState = types.SimpleNamespace(LOADED="loaded")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.callback = lambda function: function
    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.HomeAssistantError = RuntimeError

    sys.modules.update(
        {
            "renault_api": renault_api,
            "renault_api.exceptions": renault_exceptions,
            "renault_api.kamereon": kamereon,
            "renault_api.kamereon.schemas": schemas,
            "renault_api.kamereon.enums": enums,
            "renault_api.kamereon.models": models,
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.exceptions": exceptions,
        }
    )


_install_import_stubs()
module_name = f"{PACKAGE_NAME}.charge_control"
spec = importlib.util.spec_from_file_location(
    module_name,
    PACKAGE_PATH / "charge_control.py",
)
assert spec is not None and spec.loader is not None
charge_control = importlib.util.module_from_spec(spec)
sys.modules[module_name] = charge_control
spec.loader.exec_module(charge_control)


class _Response:
    raw_data = {"data": {"id": "command-id"}}

    def get_attributes(self, _schema):
        return KamereonVehicleChargingStartActionData()


class _LowLevelVehicle:
    def __init__(self) -> None:
        self.requests: list[tuple[EndpointDefinition, dict]] = []

    async def _set_vehicle_data(self, endpoint, payload):
        self.requests.append((endpoint, payload))
        return _Response()


class _Vehicle:
    def __init__(self) -> None:
        self._vehicle = _LowLevelVehicle()
        self.coordinators = {}

    async def set_charge_start(self, _when=None):
        return None

    async def set_charge_stop(self):
        return None


class ChargeControlTest(unittest.TestCase):
    """Verify commands sent to Renault's KCM endpoints."""

    def setUp(self) -> None:
        self.vehicle = _Vehicle()
        self.control = charge_control.ZoeNewChargeControl(object(), self.vehicle)
        self.control._start_confirmation = lambda _command: None

    def test_stop_uses_future_kcm_schedule(self) -> None:
        asyncio.run(self.control.async_stop())

        endpoint, payload = self.vehicle._vehicle.requests[-1]
        self.assertEqual("/kcm/v1/vehicles/{vin}/charge/schedule", endpoint.endpoint)
        self.assertEqual("kcm", endpoint.mode)
        self.assertEqual("ChargeSchedule", payload["data"]["type"])
        schedules = payload["data"]["attributes"]["schedules"]
        self.assertEqual(5, len(schedules))
        self.assertTrue(schedules[0]["activated"])
        self.assertEqual(1, sum(schedule["activated"] for schedule in schedules))
        active_days = [
            day
            for day in charge_control.CHARGE_SCHEDULE_DAYS
            if schedules[0][day] is not None
        ]
        self.assertEqual(1, len(active_days))
        self.assertEqual(1, schedules[0][active_days[0]]["duration"])
        self.assertEqual("stop", self.control.last_command)
        self.assertEqual("command-id", self.control.last_command_id)
        self.assertEqual("kcm_schedule", self.control.stop_method)
        self.assertIsNotNone(self.control.delayed_until)

    def test_start_keeps_kcm_start_endpoint(self) -> None:
        asyncio.run(self.control.async_start())

        endpoint, payload = self.vehicle._vehicle.requests[-1]
        self.assertEqual("/kcm/v1/vehicles/{vin}/charge/start", endpoint.endpoint)
        self.assertEqual("start", payload["data"]["attributes"]["action"])

    def test_delayed_start_includes_utc_timestamp(self) -> None:
        when = datetime(2026, 8, 9, 1, 45, tzinfo=timezone.utc)
        asyncio.run(self.control.async_start(when))

        _, payload = self.vehicle._vehicle.requests[-1]
        self.assertEqual(
            "2026-08-09T01:45:00.000Z",
            payload["data"]["attributes"]["startDateTime"],
        )
        self.assertEqual(when.isoformat(), self.control.delayed_until)


if __name__ == "__main__":
    unittest.main()
