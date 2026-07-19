"""Smart charging location guard for Renault Zoe New."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .charge_control import find_zoe_new
from .const import (
    CONF_ALLOW_ANY_LOCATION,
    CONF_ALLOWED_ZONES,
    CONF_LOCATION_CONTROL_ENABLED,
    ZOE_LOCATION_ENTITY_ID,
)

ATTR_IN_ZONES = "in_zones"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the smart charging location guard."""
    vehicle = find_zoe_new(hass)
    if vehicle is not None:
        async_add_entities([ZoeNewLocationAllowedSensor(config_entry, vehicle)])


class ZoeNewLocationAllowedSensor(BinarySensorEntity):
    """Allow smart charging only in the zones selected by the user."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:map-marker-check"
    _attr_name = "Smart charging location allowed"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the location guard."""
        self.config_entry = config_entry
        self._attr_device_info = vehicle.device_info
        self._attr_unique_id = (
            f"{vehicle.details.vin}_smart_charging_location_allowed".lower()
        )

    @property
    def allowed_zones(self) -> list[str]:
        """Return selected allowed zones."""
        return list(self.config_entry.options.get(CONF_ALLOWED_ZONES, []))

    @property
    def current_zones(self) -> list[str]:
        """Return zones reported by the Renault location tracker."""
        tracker = self.hass.states.get(ZOE_LOCATION_ENTITY_ID)
        if tracker is None:
            return []
        return list(tracker.attributes.get(ATTR_IN_ZONES, []))

    @property
    @override
    def is_on(self) -> bool:
        """Return whether smart charging is allowed at the current location."""
        if not self.config_entry.options.get(CONF_LOCATION_CONTROL_ENABLED, True):
            return False
        if self.config_entry.options.get(CONF_ALLOW_ANY_LOCATION, True):
            return True
        allowed = self.allowed_zones
        return bool(set(allowed).intersection(self.current_zones))

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return location diagnostics without duplicating the full tracker."""
        tracker = self.hass.states.get(ZOE_LOCATION_ENTITY_ID)
        return {
            "control_enabled": self.config_entry.options.get(
                CONF_LOCATION_CONTROL_ENABLED, True
            ),
            "allow_any_location": self.config_entry.options.get(
                CONF_ALLOW_ANY_LOCATION, True
            ),
            "allowed_zones": self.allowed_zones,
            "current_zones": self.current_zones,
            "location_entity_id": ZOE_LOCATION_ENTITY_ID,
            ATTR_LATITUDE: tracker.attributes.get(ATTR_LATITUDE) if tracker else None,
            ATTR_LONGITUDE: tracker.attributes.get(ATTR_LONGITUDE) if tracker else None,
        }

    async def async_added_to_hass(self) -> None:
        """Track Renault location changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [ZOE_LOCATION_ENTITY_ID],
                self._async_location_changed,
            )
        )

    @callback
    def _async_location_changed(self, event: Event[EventStateChangedData]) -> None:
        """Update when the vehicle reports a new location."""
        self.async_write_ha_state()
