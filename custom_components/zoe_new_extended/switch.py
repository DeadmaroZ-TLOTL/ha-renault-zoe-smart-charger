"""Switch controlling whether Zoe smart charging is allowed by location."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .charge_control import find_zoe_new
from .const import (
    CONF_ALLOW_ANY_LOCATION,
    CONF_ALLOWED_ZONES,
    CONF_LOCATION_CONTROL_ENABLED,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up smart charging location switches."""
    vehicle = find_zoe_new(hass)
    if vehicle is not None:
        zones = sorted(
            (state for state in hass.states.async_all() if state.domain == "zone"),
            key=lambda state: state.entity_id,
        )
        async_add_entities(
            [
                ZoeNewLocationControlSwitch(config_entry, vehicle),
                ZoeNewAnyLocationSwitch(config_entry, vehicle),
                *(
                    ZoeNewAllowedZoneSwitch(
                        config_entry,
                        vehicle,
                        zone.entity_id,
                        zone.name,
                    )
                    for zone in zones
                ),
            ]
        )


class _ZoeNewConfigSwitch(SwitchEntity):
    """Base switch persisting settings in the integration options."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize a Zoe configuration switch."""
        self.config_entry = config_entry
        self._attr_device_info = vehicle.device_info
        self._vin = vehicle.details.vin

    def _async_update_options(self, **changes: Any) -> None:
        """Persist integration options and trigger a state reload."""
        options = dict(self.config_entry.options)
        options.update(changes)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options=options,
        )


class ZoeNewLocationControlSwitch(_ZoeNewConfigSwitch):
    """Allow or block location-based smart charging control."""

    _attr_icon = "mdi:map-marker-check"
    _attr_name = "Smart charging location allowed"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the permission switch."""
        super().__init__(config_entry, vehicle)
        self._attr_unique_id = f"{self._vin}_smart_charging_location_control".lower()

    @property
    @override
    def is_on(self) -> bool:
        """Return whether location-based charging control is enabled."""
        return self.config_entry.options.get(CONF_LOCATION_CONTROL_ENABLED, True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow smart charging when the selected location matches."""
        self._async_update_options(**{CONF_LOCATION_CONTROL_ENABLED: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Block smart charging regardless of location."""
        self._async_update_options(**{CONF_LOCATION_CONTROL_ENABLED: False})


class ZoeNewAnyLocationSwitch(_ZoeNewConfigSwitch):
    """Allow smart charging outside named Home Assistant zones."""

    _attr_icon = "mdi:earth"
    _attr_name = "Any location"

    def __init__(self, config_entry: ConfigEntry, vehicle: Any) -> None:
        """Initialize the unrestricted location switch."""
        super().__init__(config_entry, vehicle)
        self._attr_unique_id = f"{self._vin}_smart_charging_any_location".lower()

    @property
    @override
    def is_on(self) -> bool:
        """Return whether smart charging is unrestricted by zone."""
        return self.config_entry.options.get(CONF_ALLOW_ANY_LOCATION, True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow smart charging at any location."""
        self._async_update_options(**{CONF_ALLOW_ANY_LOCATION: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Require one of the selected Home Assistant zones."""
        self._async_update_options(**{CONF_ALLOW_ANY_LOCATION: False})


class ZoeNewAllowedZoneSwitch(_ZoeNewConfigSwitch):
    """Select one Home Assistant zone for smart charging."""

    _attr_icon = "mdi:map-marker"

    def __init__(
        self,
        config_entry: ConfigEntry,
        vehicle: Any,
        zone_entity_id: str,
        zone_name: str,
    ) -> None:
        """Initialize one selectable charging zone."""
        super().__init__(config_entry, vehicle)
        self.zone_entity_id = zone_entity_id
        self._attr_name = zone_name
        self._attr_unique_id = f"{self._vin}_smart_charging_{zone_entity_id}".lower()

    @property
    @override
    def is_on(self) -> bool:
        """Return whether this zone is selected."""
        return self.zone_entity_id in self.config_entry.options.get(
            CONF_ALLOWED_ZONES, []
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Add this zone and require a selected-zone match."""
        allowed_zones = set(self.config_entry.options.get(CONF_ALLOWED_ZONES, []))
        allowed_zones.add(self.zone_entity_id)
        self._async_update_options(
            **{
                CONF_ALLOW_ANY_LOCATION: False,
                CONF_ALLOWED_ZONES: sorted(allowed_zones),
            }
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Remove this zone from the allowed set."""
        allowed_zones = set(self.config_entry.options.get(CONF_ALLOWED_ZONES, []))
        allowed_zones.discard(self.zone_entity_id)
        self._async_update_options(**{CONF_ALLOWED_ZONES: sorted(allowed_zones)})
