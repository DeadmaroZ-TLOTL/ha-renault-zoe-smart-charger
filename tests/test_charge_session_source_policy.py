"""Regression tests for completed-session operator attribution."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT_PATH = (
    Path(__file__).parents[1]
    / "smart_charger"
    / "pyscript"
    / "zoe_charge_sessions.py"
)
FUNCTIONS = {
    "_add_session_cost",
    "_is_exact_provider_session",
    "_inherit_stored_exact_provider_sessions",
}


def _load_functions() -> dict:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS
    ]
    namespace = {
        "datetime": datetime,
        "timedelta": timedelta,
        "timezone": timezone,
        "EFFECTIVE_PRICE_ENTITY": "sensor.effective_price",
        "EXACT_PROVIDER_PRICE_SOURCES": {
            "elektrum_drive_app",
            "mobilly",
            "ignitis_on_app",
            "ikrautas_app",
        },
        "_parse_datetime": lambda value: datetime.fromisoformat(value),
        "_number": lambda value, default=0.0: (
            float(value) if value is not None else default
        ),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), SCRIPT_PATH, "exec"), namespace)
    return namespace


class ChargeSessionSourcePolicyTest(unittest.TestCase):
    """Keep estimates separate from exact payment-provider transactions."""

    def setUp(self) -> None:
        self.functions = _load_functions()

    def test_station_tariff_does_not_claim_elektrum_payment_provider(self) -> None:
        self.functions["_weighted_price"] = lambda *_args: (
            40.55,
            21 * 60,
            {
                "price_source": "elektrum_drive",
                "station_name": "Augusta Deglava iela 160A",
            },
        )
        session = {
            "start": "2026-08-21T08:36:00+00:00",
            "end": "2026-08-21T08:57:00+00:00",
            "estimated_battery_energy_kwh": 16.64,
        }
        settings = {
            "charging_efficiency": 0.9,
            "delivery_price_incl_vat_eur_per_kwh": 0.0479402,
        }

        result = self.functions["_add_session_cost"](
            session,
            [],
            [],
            [],
            [],
            settings,
        )

        self.assertEqual("station_tariff_estimate", result["price_source"])
        self.assertFalse(result["operator_data_available"])
        self.assertIsNone(result["station_network"])
        self.assertNotIn("provider", result)

    def test_legacy_estimate_is_not_preserved_as_exact_operator_data(self) -> None:
        session = {
            "start": "2026-08-21T08:36:00+00:00",
            "end": "2026-08-21T08:57:00+00:00",
            "price_source": None,
        }
        stored = {
            (session["start"], session["end"]): {
                **session,
                "price_source": "elektrum_drive",
                "provider": "Elektrum Drive",
            }
        }

        result = self.functions["_inherit_stored_exact_provider_sessions"](
            [session], stored
        )[0]

        self.assertIsNone(result["price_source"])
        self.assertNotIn("provider", result)

    def test_exact_operator_transaction_survives_temporary_account_outage(self) -> None:
        session = {
            "start": "2026-08-21T08:36:00+00:00",
            "end": "2026-08-21T08:57:00+00:00",
            "price_source": None,
        }
        stored = {
            (session["start"], session["end"]): {
                **session,
                "price_source": "mobilly",
                "provider": "Mobilly",
                "provider_reported_cost": True,
                "provider_reported_energy": True,
                "operator": "Mobilly",
                "payment_provider": "Mobilly",
                "payment_provider_confirmed": True,
                "operator_data_available": True,
                "grid_energy_kwh": 17.0,
                "total_cost_eur": 6.5,
            }
        }

        result = self.functions["_inherit_stored_exact_provider_sessions"](
            [session], stored
        )[0]

        self.assertEqual("Mobilly", result["provider"])
        self.assertEqual("Mobilly", result["payment_provider"])
        self.assertTrue(result["payment_provider_confirmed"])
        self.assertTrue(result["operator_data_available"])
        self.assertEqual(6.5, result["total_cost_eur"])
        self.assertTrue(result["price_preserved_from_previous_update"])


if __name__ == "__main__":
    unittest.main()
