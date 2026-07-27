"""Charging mode control for Renault Zoe New."""

from __future__ import annotations

import asyncio
from typing import Any, override

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

MODEL_CODE = "X102VE"
OPTIONS = ("always", "delayed", "scheduled")
MODE_TO_OPTION = {
    "always": "always",
    "always_charging": "always",
    "delayed": "delayed",
    "scheduled": "scheduled",
    "schedule_mode": "scheduled",
}
OPTION_TO_COMMAND = {
    "always": "always_charging",
    "delayed": "schedule_mode",
    "scheduled": "scheduled",
}


def _normalize_mode(mode: object) -> str | None:
    """Map known API spellings while keeping delayed and scheduled distinct."""
    normalized = str(mode).strip().lower() if mode is not None else ""
    return MODE_TO_OPTION.get(normalized)


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


class ZoeNewChargingModeSelect(CoordinatorEntity, RestoreEntity, SelectEntity):
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
        self._last_option: str | None = None

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the last mode while Renault cloud data is unavailable."""
        await super().async_added_to_hass()
        if option := _normalize_mode(getattr(self.coordinator.data, "mode", None)):
            self._last_option = option
        elif (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in OPTIONS:
                self._last_option = last_state.state

    @property
    @override
    def available(self) -> bool:
        """Keep the control visible during a transient coordinator outage."""
        return (
            self.coordinator.last_update_success
            or self._pending_option is not None
            or self._last_option is not None
        )

    @property
    @override
    def current_option(self) -> str | None:
        """Return the normalized charging mode."""
        if self._pending_option is not None:
            return self._pending_option
        return (
            _normalize_mode(getattr(self.coordinator.data, "mode", None))
            or self._last_option
        )

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the charging mode and refresh its direct API state."""
        command = OPTION_TO_COMMAND[option]
        await self.vehicle.set_charge_mode(command)
        self._pending_option = option
        self._last_option = option
        self.async_write_ha_state()
        await asyncio.sleep(5)
        try:
            await self.coordinator.async_request_refresh()
        finally:
            self._pending_option = None
            self.async_write_ha_state()

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Remember each confirmed mode before writing the entity state."""
        if option := _normalize_mode(getattr(self.coordinator.data, "mode", None)):
            self._last_option = option
        super()._handle_coordinator_update()
