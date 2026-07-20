"""Diagnostic sensors for Zoe New Extended."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, override

from renault_api.kamereon.enums import ChargeState, PlugState

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .charge_control import ZoeNewChargeControl
from .const import DOMAIN
from .extras import (
    ZoeNewCloudExtrasCoordinator,
    active_contracts,
    find_contract,
)
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
    extras_coordinator = hass.data[DOMAIN][config_entry.entry_id].get(
        "extras_coordinator"
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
        if extras_coordinator is not None:
            entities.extend(
                (
                    ZoeNewCloudAlertsSensor(extras_coordinator, control),
                    ZoeNewActiveContractsSensor(extras_coordinator, control),
                    ZoeNewWarrantySensor(
                        extras_coordinator,
                        control,
                        contract_code="BatteryWarranty",
                        name="Battery warranty expiry",
                        icon="mdi:battery-heart-variant",
                    ),
                    ZoeNewWarrantySensor(
                        extras_coordinator,
                        control,
                        contract_code="CorrosionWarranty",
                        name="Corrosion warranty expiry",
                        icon="mdi:shield-car",
                    ),
                    ZoeNewRemoteServicesSensor(extras_coordinator, control),
                )
            )
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


class _ZoeNewCloudExtrasSensor(CoordinatorEntity, SensorEntity):
    """Base entity for the read-only Renault cloud extras."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZoeNewCloudExtrasCoordinator,
        control: ZoeNewChargeControl,
        unique_id_suffix: str,
    ) -> None:
        """Initialize a cloud extras sensor."""
        super().__init__(coordinator)
        self._attr_device_info = control.vehicle.device_info
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_{unique_id_suffix}".lower()
        )


class ZoeNewCloudAlertsSensor(_ZoeNewCloudExtrasSensor):
    """Expose the number of current MyRenault cloud alerts."""

    _attr_icon = "mdi:car-info"
    _attr_name = "Cloud alerts"
    _unrecorded_attributes = frozenset({"alerts"})

    def __init__(
        self,
        coordinator: ZoeNewCloudExtrasCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        """Initialize the alert sensor."""
        super().__init__(coordinator, control, "zoe_new_cloud_alerts")

    @property
    @override
    def available(self) -> bool:
        """Return whether Renault exposed the alerts endpoint."""
        return super().available and self.coordinator.data["alerts_available"]

    @property
    @override
    def native_value(self) -> int:
        """Return the current alert count."""
        return len(self.coordinator.data["alerts"])

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose alert details and the last optional-endpoint error."""
        return {
            "alerts": self.coordinator.data["alerts"],
            "last_error": self.coordinator.data["alerts_error"],
        }


class ZoeNewActiveContractsSensor(_ZoeNewCloudExtrasSensor):
    """Expose active Renault warranties and connected services."""

    _attr_icon = "mdi:file-certificate-outline"
    _attr_name = "Active contracts"
    _unrecorded_attributes = frozenset({"active_contracts", "all_contracts"})

    def __init__(
        self,
        coordinator: ZoeNewCloudExtrasCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        """Initialize the active-contract sensor."""
        super().__init__(coordinator, control, "zoe_new_active_contracts")

    @property
    @override
    def available(self) -> bool:
        """Return whether Renault exposed contract data."""
        return super().available and self.coordinator.data["contracts_available"]

    @property
    @override
    def native_value(self) -> int:
        """Return the active and confirmed contract count."""
        return len(active_contracts(self.coordinator.data))

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose all contract details without private identifiers."""
        return {
            "active_contracts": active_contracts(self.coordinator.data),
            "all_contracts": self.coordinator.data["contracts"],
            "last_error": self.coordinator.data["contracts_error"],
        }


class ZoeNewWarrantySensor(_ZoeNewCloudExtrasSensor):
    """Expose the expiry date of one Renault warranty."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: ZoeNewCloudExtrasCoordinator,
        control: ZoeNewChargeControl,
        *,
        contract_code: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize a warranty sensor."""
        super().__init__(
            coordinator,
            control,
            f"zoe_new_{contract_code.lower()}_expiry",
        )
        self.contract_code = contract_code
        self._attr_name = name
        self._attr_icon = icon

    @property
    @override
    def available(self) -> bool:
        """Return whether this warranty is present in Renault data."""
        return (
            super().available
            and self.coordinator.data["contracts_available"]
            and self._contract is not None
            and self._contract.get("end_date") is not None
        )

    @property
    def _contract(self) -> dict[str, Any] | None:
        return find_contract(self.coordinator.data, code=self.contract_code)

    @property
    @override
    def native_value(self) -> date | None:
        """Return the warranty expiry date."""
        contract = self._contract
        if contract is None or contract.get("end_date") is None:
            return None
        return date.fromisoformat(contract["end_date"])

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the current warranty status."""
        contract = self._contract or {}
        return {
            "status": contract.get("status"),
            "status_label": contract.get("status_label"),
            "description": contract.get("description"),
        }


class ZoeNewRemoteServicesSensor(_ZoeNewCloudExtrasSensor):
    """Expose the My Remote Services contract state."""

    _attr_icon = "mdi:car-connected"
    _attr_name = "My Remote Services"

    def __init__(
        self,
        coordinator: ZoeNewCloudExtrasCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        """Initialize the connected-services sensor."""
        super().__init__(coordinator, control, "zoe_new_remote_services")

    @property
    def _contract(self) -> dict[str, Any] | None:
        return find_contract(self.coordinator.data, code="14709")

    @property
    @override
    def available(self) -> bool:
        """Return whether My Remote Services is present."""
        return (
            super().available
            and self.coordinator.data["contracts_available"]
            and self._contract is not None
        )

    @property
    @override
    def native_value(self) -> str | None:
        """Return the Renault contract state."""
        contract = self._contract
        status = contract.get("status") if contract else None
        return status.lower() if status else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the remote-services contract details."""
        contract = self._contract or {}
        return {
            "status_label": contract.get("status_label"),
            "description": contract.get("description"),
            "start_date": contract.get("start_date"),
            "end_date": contract.get("end_date"),
        }
