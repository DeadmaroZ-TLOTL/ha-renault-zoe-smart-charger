"""Tests for retained Renault trip and surface history validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "trip_history_data.py"
)
SPEC = importlib.util.spec_from_file_location("trip_history_data", MODULE_PATH)
trip_history_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trip_history_data)


class TripHistoryDataTest(unittest.TestCase):
    """Verify normalization and rejection of unsafe records."""

    def test_normalizes_surface_to_odometer_distance(self) -> None:
        records = trip_history_data.normalize_trip_records(
            [
                {
                    "id": "trip:1000:2000:100",
                    "day": "2026-08-20",
                    "start": 1000,
                    "end": 2000,
                    "km": 10,
                    "hard": 9,
                    "loose": 3,
                    "unknown": 0,
                    "coverage": 1,
                    "average_speed": 42.345,
                    "max_speed": 80,
                }
            ]
        )
        self.assertEqual(records[0]["hard"], 7.5)
        self.assertEqual(records[0]["loose"], 2.5)
        self.assertEqual(records[0]["unknown"], 0)
        self.assertEqual(records[0]["coverage"], 100)
        self.assertEqual(records[0]["average_speed"], 42.34)

    def test_replaces_duplicate_ids_and_sorts(self) -> None:
        records = trip_history_data.normalize_trip_records(
            [
                {
                    "id": "later",
                    "day": "2026-08-21",
                    "start": 3000,
                    "end": 4000,
                    "km": 2,
                    "hard": 0,
                    "loose": 0,
                    "unknown": 2,
                },
                {
                    "id": "same",
                    "day": "2026-08-20",
                    "start": 1000,
                    "end": 2000,
                    "km": 1,
                    "hard": 1,
                    "loose": 0,
                    "unknown": 0,
                },
                {
                    "id": "same",
                    "day": "2026-08-20",
                    "start": 1000,
                    "end": 2000,
                    "km": 1.5,
                    "hard": 1,
                    "loose": 0,
                    "unknown": 0.5,
                },
            ]
        )
        self.assertEqual([record["id"] for record in records], ["same", "later"])
        self.assertEqual(records[0]["km"], 1.5)

    def test_rejects_invalid_records(self) -> None:
        invalid = {
            "id": "bad id",
            "day": "2026-08-20",
            "start": 1000,
            "end": 2000,
            "km": 1,
            "hard": 1,
            "loose": 0,
            "unknown": 0,
        }
        with self.assertRaises(ValueError):
            trip_history_data.normalize_trip_records([invalid])


if __name__ == "__main__":
    unittest.main()
