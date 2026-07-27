"""Smart charging location guard for Renault Zoe New."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .charge_control import find_zoe_new
from .const import (
    CONF_ALLOW_ANY_LOCATION,
    CONF_ALLOWED_ZONES,
    CONF_IMMAX_CHARGER_ONLINE_ENTITY,
    CONF_IMMAX_CHARGER_PROBLEM_ENTITY,
    CONF_LOCATION_CONTROL_ENABLED,
    DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY,
    DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY,
    ZOE_LOCATION_ENTITY_ID,
)

ATTR_IN_ZONES = "in_zones"


@dataclass(frozen=True, kw_only=True)
class ImmaxProxyBinarySensorDescription(BinarySensorEntityDescription):
    """Describe one configurable IMMAX binary source."""

    option_key: str
    default_entity_id: str


IMMAX_PROXY_BINARY_SENSOR_DESCRIPTIONS = (
    ImmaxProxyBinarySensorDescription(
        key="renault_zoe_new_immax_online",
        name="IMMAX online",
        icon="mdi:lan-connect",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        option_key=CONF_IMMAX_CHARGER_ONLINE_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY,
    ),
    ImmaxProxyBinarySensorDescription(
        key="renault_zoe_new_immax_problem",
        name="IMMAX problem",
        icon="mdi:alert-circle-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        option_key=CONF_IMMAX_CHARGER_PROBLEM_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the smart charging location guard."""
    vehicle = find_zoe_new(hass)
    if vehicle is not None:
        async_add_entities(
            [
                ZoeNewLocationAllowedSensor(config_entry, vehicle),
                *(
                    ZoeNewImmaxProxyBinarySensor(
                        config_entry,
                        vehicle,
                        description,
                    )
                    for description in IMMAX_PROXY_BINARY_SENSOR_DESCRIPTIONS
                ),
            ]
        )


class ZoeNewImmaxProxyBinarySensor(BinarySensorEntity):
    """Expose a user-selected on/off source under a stable entity ID."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        vehicle: Any,
        description: ImmaxProxyBinarySensorDescription,
    ) -> None:
        """Initialize a configurable binary source proxy."""
        self.config_entry = config_entry
        self.entity_description = description
        self._attr_device_info = vehicle.device_info
        self._attr_unique_id = f"{vehicle.details.vin}_{description.key}".lower()
        self._attr_suggested_object_id = description.key

    @property
    def source_entity_id(self) -> str | None:
        """Return the selected source entity."""
        return (
            self.config_entry.options.get(
                self.entity_description.option_key,
                self.entity_description.default_entity_id,
            )
            or None
        )

    @property
    def source_state(self) -> State | None:
        """Return the selected source state."""
        source_entity_id = self.source_entity_id
        return self.hass.states.get(source_entity_id) if source_entity_id else None

    @property
    @override
    def available(self) -> bool:
        """Return whether the selected source is available."""
        source = self.source_state
        return source is not None and source.state not in {
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        }

    @property
    @override
    def is_on(self) -> bool:
        """Mirror the selected source's on state."""
        source = self.source_state
        return source is not None and source.state == "on"

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose which entity supplies this state."""
        return {
            "source_entity_id": self.source_entity_id,
            "configured": self.source_entity_id is not None,
        }

    async def async_added_to_hass(self) -> None:
        """Track the selected source entity."""
        await super().async_added_to_hass()
        source_entity_id = self.source_entity_id
        if source_entity_id is None:
            return
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [source_entity_id],
                self._async_source_changed,
            )
        )

    @callback
    def _async_source_changed(self, event: Event[EventStateChangedData]) -> None:
        """Publish every source update immediately."""
        self.async_write_ha_state()


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
