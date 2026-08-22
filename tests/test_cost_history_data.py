"""Tests for persisted Renault daily-cost records."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "cost_history_data.py"
)
SPEC = importlib.util.spec_from_file_location("cost_history_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
cost_history_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cost_history_data)


class CostHistoryDataTest(unittest.TestCase):
    """Verify daily totals are safe and deterministic."""

    def test_normalizes_sorts_and_replaces_duplicate_days(self) -> None:
        records = cost_history_data.normalize_cost_days(
            [
                {
                    "day": "2026-08-02",
                    "km": "10.1239",
                    "energy_kwh": 1.2349,
                    "cost_eur": 0.45678,
                    "trips": "2",
                },
                {
                    "day": "2026-08-01",
                    "km": 5,
                    "energy_kwh": 1,
                    "cost_eur": 0.2,
                    "trips": 1,
                },
                {
                    "day": "2026-08-02",
                    "km": 12,
                    "energy_kwh": 2,
                    "cost_eur": 0.8,
                    "trips": 3,
                },
            ]
        )

        self.assertEqual(
            ["2026-08-01", "2026-08-02"],
            [row["day"] for row in records],
        )
        self.assertEqual(12.0, records[1]["km"])
        self.assertEqual(3, records[1]["trips"])

    def test_rejects_invalid_day_or_negative_values(self) -> None:
        with self.assertRaises(ValueError):
            cost_history_data.normalize_cost_days([{"day": "01.08.2026"}])
        with self.assertRaises(ValueError):
            cost_history_data.normalize_cost_days(
                [{"day": "2026-08-01", "cost_eur": -0.1}]
            )


if __name__ == "__main__":
    unittest.main()
