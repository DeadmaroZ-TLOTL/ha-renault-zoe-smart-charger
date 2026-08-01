"""Adaptive refresh interval for live Zoe New charging data."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.core import callback

ACTIVE_UPDATE_INTERVAL = timedelta(minutes=5)
ACTIVE_PLUG_STATES = {"plugged", "plugged_waiting_for_charge"}


class ZoeNewStatusRefresh:
    """Refresh battery and charging status faster while the car is plugged in."""

    def __init__(self, vehicle: Any) -> None:
        """Attach to the Renault battery coordinator."""
        self.coordinator = vehicle.coordinators["battery"]
        self._original_interval = self.coordinator.update_interval
        self._unsubscribe: Callable[[], None] = self.coordinator.async_add_listener(
            self._handle_update
        )
        self._handle_update()

    @callback
    def _handle_update(self) -> None:
        """Use the faster interval only while the vehicle is connected."""
        data = self.coordinator.data
        plug_state = data.get_plug_status() if data is not None else None
        plug_name = getattr(plug_state, "name", "").casefold()
        desired_interval = self._original_interval
        if plug_name in ACTIVE_PLUG_STATES and (
            desired_interval is None or desired_interval > ACTIVE_UPDATE_INTERVAL
        ):
            desired_interval = ACTIVE_UPDATE_INTERVAL

        if self.coordinator.update_interval != desired_interval:
            self.coordinator.update_interval = desired_interval

    async def async_refresh(self) -> None:
        """Request one immediate battery status refresh."""
        await self.coordinator.async_request_refresh()

    @callback
    def restore(self) -> None:
        """Restore the Renault integration's original polling interval."""
        self._unsubscribe()
        self.coordinator.update_interval = self._original_interval
