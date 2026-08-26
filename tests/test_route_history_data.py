"""Tests for retained Renault GPS route points."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zoe_new_extended"
    / "route_history_data.py"
)
SPEC = importlib.util.spec_from_file_location("route_history_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
route_history_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route_history_data)


class RouteHistoryDataTest(unittest.TestCase):
    """Verify GPS history is validated, ordered, and deterministic."""

    def test_normalizes_orders_and_replaces_duplicate_timestamps(self) -> None:
        points = route_history_data.normalize_route_points(
            [
                {"t": "2000", "lat": "56.95", "lon": "24.10"},
                {"t": 1000, "lat": 56.9, "lon": 24.2, "accuracy": 5.55},
                {"t": 2000, "lat": 56.96, "lon": 24.11},
            ]
        )

        self.assertEqual([1000, 2000], [point["t"] for point in points])
        self.assertEqual(5.5, points[0]["accuracy"])
        self.assertEqual(56.96, points[1]["lat"])

    def test_rejects_invalid_coordinates_and_accuracy(self) -> None:
        with self.assertRaises(ValueError):
            route_history_data.normalize_route_points(
                [{"t": 1, "lat": 91, "lon": 24}]
            )
        with self.assertRaises(ValueError):
            route_history_data.normalize_route_points(
                [{"t": 1, "lat": 56, "lon": 24, "accuracy": -1}]
            )


if __name__ == "__main__":
    unittest.main()
