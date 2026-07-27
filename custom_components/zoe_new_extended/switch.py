"""Location controls for Zoe smart charging."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .charge_control import find_zoe_new
from .const import (
    CONF_ALLOW_ANY_LOCATION,
    CONF_IMMAX_CHARGER_SWITCH_ENTITY,
    CONF_LOCATION_CONTROL_ENABLED,
    DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the global smart-charging location controls."""
    vehicle = find_zoe_new(hass)
    if vehicle is not None:
        async_add_entities(
            [
                ZoeNewLocationControlSwitch(config_entry, vehicle),
                ZoeNewAnyLocationSwitch(config_entry, vehicle),
                ZoeNewImmaxChargingSwitch(config_entry, vehicle),
            ]
        )


class ZoeNewImmaxChargingSwitch(SwitchEntity):
    """Control the selected IMMAX charger switch through a stable entity."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"
    _attr_name = "IMMAX charging"
    _attr_suggested_object_id = "renault_zoe_new_immax_charging"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the configurable charger switch proxy."""
        self.config_entry = config_entry
        self._attr_device_info = vehicle.device_info
        self._attr_unique_id = f"{vehicle.details.vin}_immax_charging".lower()

    @property
    def source_entity_id(self) -> str:
        """Return the selected charger switch."""
        return self.config_entry.options.get(
            CONF_IMMAX_CHARGER_SWITCH_ENTITY,
            DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY,
        )

    @property
    def source_state(self) -> State | None:
        """Return the selected charger state."""
        return self.hass.states.get(self.source_entity_id)

    @property
    @override
    def available(self) -> bool:
        """Return whether the selected charger switch is available."""
        source = self.source_state
        return source is not None and source.state not in {
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        }

    @property
    @override
    def is_on(self) -> bool:
        """Mirror the selected charger switch."""
        source = self.source_state
        return source is not None and source.state == "on"

    @property
    @override
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose which entity receives control commands."""
        return {"source_entity_id": self.source_entity_id}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the selected charger switch."""
        await self.hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": self.source_entity_id},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the selected charger switch."""
        await self.hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": self.source_entity_id},
            blocking=True,
        )

    async def async_added_to_hass(self) -> None:
        """Track the selected charger switch."""
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


class _ZoeNewConfigSwitch(SwitchEntity):
    """Base switch persisting a Zoe New Extended option."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize a configuration switch."""
        self.config_entry = config_entry
        self._attr_device_info = vehicle.device_info
        self._vin = vehicle.details.vin

    def _async_update_option(self, option: str, value: bool) -> None:
        """Persist one integration option."""
        options = dict(self.config_entry.options)
        options[option] = value
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options=options,
        )


class ZoeNewLocationControlSwitch(_ZoeNewConfigSwitch):
    """Enable or disable the smart-charging location guard."""

    _attr_icon = "mdi:map-marker-check"
    _attr_name = "Smart charging location allowed"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the location guard switch."""
        super().__init__(config_entry, vehicle)
        self._attr_unique_id = f"{self._vin}_smart_charging_location_control".lower()

    @property
    @override
    def is_on(self) -> bool:
        """Return whether smart charging is allowed by location settings."""
        return self.config_entry.options.get(CONF_LOCATION_CONTROL_ENABLED, True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable location-based smart charging."""
        self._async_update_option(CONF_LOCATION_CONTROL_ENABLED, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable location-based smart charging."""
        self._async_update_option(CONF_LOCATION_CONTROL_ENABLED, False)


class ZoeNewAnyLocationSwitch(_ZoeNewConfigSwitch):
    """Allow smart charging outside the configured Home Assistant zones."""

    _attr_icon = "mdi:earth"
    _attr_name = "Allow at any location"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the unrestricted-location switch."""
        super().__init__(config_entry, vehicle)
        self._attr_unique_id = f"{self._vin}_smart_charging_any_location".lower()

    @property
    @override
    def is_on(self) -> bool:
        """Return whether every location is allowed."""
        return self.config_entry.options.get(CONF_ALLOW_ANY_LOCATION, True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow smart charging at any location."""
        self._async_update_option(CONF_ALLOW_ANY_LOCATION, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Require a match with one of the configured zones."""
        self._async_update_option(CONF_ALLOW_ANY_LOCATION, False)
