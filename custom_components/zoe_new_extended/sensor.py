"""Diagnostic sensors for Zoe New Extended."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import override

from renault_api.kamereon.enums import ChargeState, PlugState

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .charge_control import ZoeNewChargeControl
from .const import DOMAIN
from .nordpool import NordPoolPriceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the command status sensor."""
    control = hass.data[DOMAIN][config_entry.entry_id].get("charge_control")
    nordpool_coordinator = hass.data[DOMAIN][config_entry.entry_id].get(
        "nordpool_coordinator"
    )
    entities: list[SensorEntity] = []
    if control is not None:
        entities.extend(
            (
                ZoeNewChargeCommandSensor(control),
                ZoeNewApiLastUpdatedSensor(control),
                ZoeNewRawChargeStatusSensor(control),
                ZoeNewRawPlugStatusSensor(control),
            )
        )
        if nordpool_coordinator is not None:
            entities.append(ZoeNordPoolPriceSensor(nordpool_coordinator, control))
    async_add_entities(entities)


class ZoeNordPoolPriceSensor(CoordinatorEntity, SensorEntity):
    """Expose the Nord Pool price selected in integration options."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_has_entity_name = True
    _attr_icon = "mdi:transmission-tower"
    _attr_name = "Nord Pool price"
    _attr_native_unit_of_measurement = "c/kWh"
    _attr_suggested_object_id = "renault_zoe_new_nord_pool_price"
    _unrecorded_attributes = frozenset(
        {"today", "tomorrow", "raw_today", "raw_tomorrow"}
    )

    def __init__(
        self,
        coordinator: NordPoolPriceCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        """Initialize the selected-area price sensor."""
        super().__init__(coordinator)
        self._attr_device_info = control.vehicle.device_info
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_zoe_new_nord_pool_price".lower()
        )

    @property
    @override
    def available(self) -> bool:
        """Return whether a current interval price is available."""
        return super().available and self.coordinator.data.get("value") is not None

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current selected-area price in cents per kWh."""
        return self.coordinator.data.get("value")

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose planner-compatible raw intervals and source details."""
        return {
            key: value for key, value in self.coordinator.data.items() if key != "value"
        }


class ZoeNewChargeCommandSensor(SensorEntity):
    """Expose accepted and confirmed Renault charge command state."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"
    _attr_name = "Charge command"

    def __init__(self, control: ZoeNewChargeControl) -> None:
        """Initialize the sensor."""
        self.control = control
        self._attr_device_info = control.vehicle.device_info
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_zoe_new_charge_command".lower()
        )

    @property
    @override
    def native_value(self) -> str:
        """Return the current command state."""
        return self.control.state

    @property
    @override
    def extra_state_attributes(self):
        """Return command diagnostics."""
        return self.control.extra_state_attributes

    async def async_added_to_hass(self) -> None:
        """Register for command state updates."""
        await super().async_added_to_hass()
        self.async_on_remove(self.control.async_add_listener(self.async_write_ha_state))


class _ZoeNewRawStatusSensor(CoordinatorEntity, SensorEntity):
    """Base sensor exposing the API enum name without UI translation."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, control: ZoeNewChargeControl) -> None:
        """Initialize from the Renault battery coordinator."""
        super().__init__(control.vehicle.coordinators["battery"])
        self.control = control
        self._attr_device_info = control.vehicle.device_info


class ZoeNewApiLastUpdatedSensor(CoordinatorEntity, SensorEntity):
    """Expose the time of the latest successful Renault status refresh."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-check-outline"
    _attr_name = "API last updated"

    def __init__(self, control: ZoeNewChargeControl) -> None:
        """Initialize from the Renault battery coordinator."""
        coordinator = control.vehicle.coordinators["battery"]
        super().__init__(coordinator)
        self._attr_device_info = control.vehicle.device_info
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_zoe_new_api_last_updated".lower()
        )
        self._attr_native_value = (
            datetime.now(UTC) if coordinator.last_update_success else None
        )

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Record every successful API status refresh, even if data is unchanged."""
        if self.coordinator.last_update_success:
            self._attr_native_value = datetime.now(UTC)
        self.async_write_ha_state()


class ZoeNewRawChargeStatusSensor(_ZoeNewRawStatusSensor):
    """Expose the raw Renault charge state and every known state code."""

    _attr_icon = "mdi:ev-plug-type2"
    _attr_name = "Raw charge status"

    def __init__(self, control: ZoeNewChargeControl) -> None:
        """Initialize the raw charge status sensor."""
        super().__init__(control)
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_zoe_new_raw_charge_status".lower()
        )

    @property
    @override
    def native_value(self) -> str | None:
        """Return the exact API enum name."""
        state = self.coordinator.data.get_charging_status()
        return state.name.lower() if state is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        """List all known charge states and their raw API codes."""
        return {
            "supported_statuses": [state.name.lower() for state in ChargeState],
            "status_codes": {state.name.lower(): state.value for state in ChargeState},
        }


class ZoeNewRawPlugStatusSensor(_ZoeNewRawStatusSensor):
    """Expose the raw Renault plug state and every known state code."""

    _attr_icon = "mdi:power-plug"
    _attr_name = "Raw plug status"

    def __init__(self, control: ZoeNewChargeControl) -> None:
        """Initialize the raw plug status sensor."""
        super().__init__(control)
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_zoe_new_raw_plug_status".lower()
        )

    @property
    @override
    def native_value(self) -> str | None:
        """Return the exact API enum name."""
        state = self.coordinator.data.get_plug_status()
        return state.name.lower() if state is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        """List all known plug states and their raw API codes."""
        return {
            "supported_statuses": [state.name.lower() for state in PlugState],
            "status_codes": {state.name.lower(): state.value for state in PlugState},
        }
