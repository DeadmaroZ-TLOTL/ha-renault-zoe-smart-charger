"""Location controls for Zoe smart charging."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .charge_control import find_zoe_new
from .const import CONF_ALLOW_ANY_LOCATION, CONF_LOCATION_CONTROL_ENABLED


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
            ]
        )


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
