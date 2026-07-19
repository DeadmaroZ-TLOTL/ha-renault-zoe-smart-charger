"""Charging mode control for Renault Zoe New."""

from __future__ import annotations

import asyncio
from typing import Any, override

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

MODEL_CODE = "X102VE"
OPTIONS = ("always", "delayed")
MODE_TO_OPTION = {
    "always": "always",
    "always_charging": "always",
    "delayed": "delayed",
    "delegated": "delayed",
    "scheduled": "delayed",
    "schedule_mode": "delayed",
}
OPTION_TO_COMMAND = {
    "always": "always_charging",
    "delayed": "schedule_mode",
}


def _normalize_mode(mode: object) -> str:
    """Map every scheduled-like or missing API mode to Delayed."""
    normalized = str(mode).strip().lower() if mode is not None else ""
    return MODE_TO_OPTION.get(normalized, "delayed")


def _find_zoe_new(hass: HomeAssistant) -> Any | None:
    for renault_entry in hass.config_entries.async_entries("renault"):
        runtime = renault_entry.runtime_data
        if runtime is None:
            continue
        for vehicle in runtime.vehicles.values():
            if vehicle.details.get_model_code() == MODEL_CODE:
                return vehicle
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Zoe New charging mode select."""
    vehicle = _find_zoe_new(hass)
    if (
        vehicle is None
        or "charging_settings" not in vehicle.coordinators
        or not vehicle.details.supports_endpoint("actions/charge-set-mode")
    ):
        return
    async_add_entities([ZoeNewChargingModeSelect(vehicle)])


class ZoeNewChargingModeSelect(CoordinatorEntity, SelectEntity):
    """Expose the writable charging mode missing from the core integration."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"
    _attr_options = list(OPTIONS)
    _attr_translation_key = "charging_mode"

    def __init__(self, vehicle: Any) -> None:
        """Initialize the select from the charging-settings coordinator."""
        super().__init__(vehicle.coordinators["charging_settings"])
        self.vehicle = vehicle
        self._attr_device_info = vehicle.device_info
        self._attr_unique_id = (
            f"{vehicle.details.vin}_zoe_new_extended_charging_mode".lower()
        )
        self._pending_option: str | None = None

    @property
    @override
    def current_option(self) -> str | None:
        """Return the normalized charging mode."""
        if self._pending_option is not None:
            return self._pending_option
        return _normalize_mode(getattr(self.coordinator.data, "mode", None))

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the charging mode and refresh its direct API state."""
        command = OPTION_TO_COMMAND[option]
        await self.vehicle.set_charge_mode(command)
        self._pending_option = option
        self.async_write_ha_state()
        await asyncio.sleep(5)
        try:
            await self.coordinator.async_request_refresh()
        finally:
            self._pending_option = None
            self.async_write_ha_state()
