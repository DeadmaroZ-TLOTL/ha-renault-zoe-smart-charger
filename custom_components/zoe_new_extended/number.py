"""Configurable IMMAX number controls for Zoe New Extended."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .charge_control import find_zoe_new
from .const import (
    CONF_IMMAX_CHARGER_CURRENT_ENTITY,
    DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY,
)
from .device_info import SOURCE_IMMAX, source_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the selected IMMAX current control."""
    vehicle = find_zoe_new(hass)
    if vehicle is not None:
        async_add_entities([ZoeNewImmaxCurrentNumber(config_entry, vehicle)])


class ZoeNewImmaxCurrentNumber(NumberEntity):
    """Control the selected charger-current number through a stable entity."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:current-ac"
    _attr_mode = NumberMode.BOX
    _attr_name = "IMMAX current"
    _attr_suggested_object_id = "renault_zoe_new_immax_current"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the configurable current-number proxy."""
        self.config_entry = config_entry
        self._attr_device_info = source_device_info(vehicle, SOURCE_IMMAX)
        self._attr_unique_id = f"{vehicle.details.vin}_immax_current".lower()

    @property
    def source_entity_id(self) -> str:
        """Return the selected charger-current entity."""
        return self.config_entry.options.get(
            CONF_IMMAX_CHARGER_CURRENT_ENTITY,
            DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY,
        )

    @property
    def source_state(self) -> State | None:
        """Return the selected current state."""
        return self.hass.states.get(self.source_entity_id)

    @property
    @override
    def available(self) -> bool:
        """Return whether the selected current control is available."""
        source = self.source_state
        return source is not None and source.state not in {
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        }

    @property
    @override
    def native_value(self) -> float | None:
        """Mirror the selected current value."""
        source = self.source_state
        if source is None or source.state in {STATE_UNAVAILABLE, STATE_UNKNOWN}:
            return None
        try:
            return float(source.state)
        except ValueError:
            return None

    @property
    @override
    def native_min_value(self) -> float:
        """Mirror the selected control minimum."""
        source = self.source_state
        return float(source.attributes.get("min", 6)) if source else 6

    @property
    @override
    def native_max_value(self) -> float:
        """Mirror the selected control maximum."""
        source = self.source_state
        return float(source.attributes.get("max", 32)) if source else 32

    @property
    @override
    def native_step(self) -> float:
        """Mirror the selected control step."""
        source = self.source_state
        return float(source.attributes.get("step", 1)) if source else 1

    @property
    @override
    def native_unit_of_measurement(self) -> str | None:
        """Mirror the selected control unit."""
        source = self.source_state
        return source.attributes.get("unit_of_measurement") if source else "A"

    @property
    @override
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose which entity receives current commands."""
        return {"source_entity_id": self.source_entity_id}

    async def async_set_native_value(self, value: float) -> None:
        """Set the selected charger-current number."""
        await self.hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": self.source_entity_id,
                "value": value,
            },
            blocking=True,
        )

    async def async_added_to_hass(self) -> None:
        """Track the selected current entity."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.source_entity_id],
                self._async_source_changed,
            )
        )

    @callback
    def _async_source_changed(self, event: Event[EventStateChangedData]) -> None:
        """Publish every selected-source update immediately."""
        self.async_write_ha_state()
