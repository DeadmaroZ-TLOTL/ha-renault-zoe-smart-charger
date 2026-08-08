"""Diagnostic sensors for Zoe New Extended."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, override

from renault_api.kamereon.enums import ChargeState, PlugState

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .charge_control import ZoeNewChargeControl
from .charging_accounts import ChargingAccountsCoordinator
from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_CHARGING_EFFICIENCY_PERCENT,
    CONF_DASHBOARD_LANGUAGE,
    CONF_DEFAULT_CHARGING_POWER_KW,
    CONF_DELIVERY_PRICE_EXCL_VAT,
    CONF_ELEKTRUM_DRIVE_ENABLED,
    CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
    CONF_ENERGY_VAT_PERCENT,
    CONF_FALLBACK_CONSUMPTION_KWH_100,
    CONF_IMMAX_BATTERY_CHARGE_ENTITY,
    CONF_IMMAX_BATTERY_DISCHARGE_ENTITY,
    CONF_IMMAX_CHARGER_ENERGY_ENTITY,
    CONF_IMMAX_CHARGER_STATUS_ENTITY,
    CONF_IMMAX_CURRENT_A_ENTITY,
    CONF_IMMAX_CURRENT_B_ENTITY,
    CONF_IMMAX_CURRENT_C_ENTITY,
    CONF_IMMAX_FEATURE_ENABLED,
    CONF_IMMAX_GRID_EXPORT_ENTITY,
    CONF_IMMAX_NORDPOOL_PRICE_ENTITY,
    CONF_IMMAX_POWER_A_ENTITY,
    CONF_IMMAX_POWER_B_ENTITY,
    CONF_IMMAX_POWER_C_ENTITY,
    CONF_IMMAX_SOLAR_POWER_ENTITY,
    CONF_IMMAX_TOTAL_LOAD_ENTITY,
    CONF_IMMAX_VEHICLE_SOC_ENTITY,
    CONF_IMMAX_VOLTAGE_A_ENTITY,
    CONF_IMMAX_VOLTAGE_B_ENTITY,
    CONF_IMMAX_VOLTAGE_C_ENTITY,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_CHARGING_EFFICIENCY_PERCENT,
    DEFAULT_DASHBOARD_LANGUAGE,
    DEFAULT_DEFAULT_CHARGING_POWER_KW,
    DEFAULT_DELIVERY_PRICE_EXCL_VAT,
    DEFAULT_ELEKTRUM_DRIVE_ENABLED,
    DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
    DEFAULT_ENERGY_VAT_PERCENT,
    DEFAULT_FALLBACK_CONSUMPTION_KWH_100,
    DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY,
    DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY,
    DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY,
    DEFAULT_IMMAX_CHARGER_STATUS_ENTITY,
    DEFAULT_IMMAX_CURRENT_A_ENTITY,
    DEFAULT_IMMAX_CURRENT_B_ENTITY,
    DEFAULT_IMMAX_CURRENT_C_ENTITY,
    DEFAULT_IMMAX_FEATURE_ENABLED,
    DEFAULT_IMMAX_GRID_EXPORT_ENTITY,
    DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY,
    DEFAULT_IMMAX_POWER_A_ENTITY,
    DEFAULT_IMMAX_POWER_B_ENTITY,
    DEFAULT_IMMAX_POWER_C_ENTITY,
    DEFAULT_IMMAX_SOLAR_POWER_ENTITY,
    DEFAULT_IMMAX_TOTAL_LOAD_ENTITY,
    DEFAULT_IMMAX_VEHICLE_SOC_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_A_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_B_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_C_ENTITY,
    DOMAIN,
)
from .elektrum_drive import ElektrumDriveCoordinator
from .device_info import (
    SOURCE_CHARGING_ACCOUNTS,
    SOURCE_IMMAX,
    SOURCE_NORDPOOL,
    SOURCE_SMART_CHARGING,
    SOURCE_ZOE_API,
    source_device_info,
)
from .extras import (
    ZoeNewCloudExtrasCoordinator,
    active_contracts,
    find_contract,
)
from .nordpool import NordPoolPriceCoordinator


@dataclass(frozen=True, kw_only=True)
class ImmaxProxySensorEntityDescription(SensorEntityDescription):
    """Describe one configurable IMMAX source sensor."""

    option_key: str | None
    default_entity_id: str


IMMAX_PROXY_SENSOR_DESCRIPTIONS = (
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_status",
        name="IMMAX status",
        icon="mdi:ev-station",
        option_key=CONF_IMMAX_CHARGER_STATUS_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CHARGER_STATUS_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_total_load",
        name="IMMAX total site load",
        icon="mdi:meter-electric-outline",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_TOTAL_LOAD_ENTITY,
        default_entity_id=DEFAULT_IMMAX_TOTAL_LOAD_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_power_a",
        name="IMMAX power A",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_POWER_A_ENTITY,
        default_entity_id=DEFAULT_IMMAX_POWER_A_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_power_b",
        name="IMMAX power B",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_POWER_B_ENTITY,
        default_entity_id=DEFAULT_IMMAX_POWER_B_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_power_c",
        name="IMMAX power C",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_POWER_C_ENTITY,
        default_entity_id=DEFAULT_IMMAX_POWER_C_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_current_a",
        name="IMMAX current A",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_CURRENT_A_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CURRENT_A_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_current_b",
        name="IMMAX current B",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_CURRENT_B_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CURRENT_B_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_current_c",
        name="IMMAX current C",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_CURRENT_C_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CURRENT_C_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_voltage_a",
        name="IMMAX voltage A",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_VOLTAGE_A_ENTITY,
        default_entity_id=DEFAULT_IMMAX_VOLTAGE_A_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_voltage_b",
        name="IMMAX voltage B",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_VOLTAGE_B_ENTITY,
        default_entity_id=DEFAULT_IMMAX_VOLTAGE_B_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_voltage_c",
        name="IMMAX voltage C",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_VOLTAGE_C_ENTITY,
        default_entity_id=DEFAULT_IMMAX_VOLTAGE_C_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_energy",
        name="IMMAX energy",
        icon="mdi:counter",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        option_key=CONF_IMMAX_CHARGER_ENERGY_ENTITY,
        default_entity_id=DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_solar_production",
        name="IMMAX solar production",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_SOLAR_POWER_ENTITY,
        default_entity_id=DEFAULT_IMMAX_SOLAR_POWER_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_grid_export",
        name="IMMAX grid export",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_GRID_EXPORT_ENTITY,
        default_entity_id=DEFAULT_IMMAX_GRID_EXPORT_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_battery_charge",
        name="IMMAX battery charging",
        icon="mdi:battery-arrow-up",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_BATTERY_CHARGE_ENTITY,
        default_entity_id=DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_battery_discharge",
        name="IMMAX battery discharging",
        icon="mdi:battery-arrow-down",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_BATTERY_DISCHARGE_ENTITY,
        default_entity_id=DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_vehicle_soc",
        name="IMMAX vehicle SOC",
        icon="mdi:battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=CONF_IMMAX_VEHICLE_SOC_ENTITY,
        default_entity_id=DEFAULT_IMMAX_VEHICLE_SOC_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="renault_zoe_new_immax_nord_pool_price",
        name="IMMAX Nord Pool price",
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.MONETARY,
        option_key=CONF_IMMAX_NORDPOOL_PRICE_ENTITY,
        default_entity_id=DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY,
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_smart_charge_status",
        name="IMMAX smart charge status",
        icon="mdi:text-box-check-outline",
        option_key=None,
        default_entity_id="input_text.immax_smart_charge_status",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_phase_mode",
        name="IMMAX detected phase mode",
        icon="mdi:sine-wave",
        option_key=None,
        default_entity_id="input_select.immax_detected_solar_phase_mode",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_planned_charging_times",
        name="IMMAX planned charging times",
        icon="mdi:calendar-clock",
        option_key=None,
        default_entity_id="input_text.immax_planned_charging_times",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_planned_energy",
        name="IMMAX planned energy",
        icon="mdi:battery-clock-outline",
        device_class=SensorDeviceClass.ENERGY,
        option_key=None,
        default_entity_id="input_number.immax_planned_energy",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_estimated_charge_cost",
        name="IMMAX estimated charge cost",
        icon="mdi:cash-clock",
        device_class=SensorDeviceClass.MONETARY,
        option_key=None,
        default_entity_id="input_number.immax_estimated_charge_cost",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_available_power",
        name="IMMAX solar available power",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=None,
        default_entity_id="input_number.immax_solar_available_power",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_target_power",
        name="IMMAX solar target power",
        icon="mdi:ev-station",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=None,
        default_entity_id="input_number.immax_solar_target_power",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_charger_power",
        name="IMMAX solar charger power",
        icon="mdi:ev-plug-type2",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=None,
        default_entity_id="input_number.immax_solar_charger_power",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_grid_export",
        name="IMMAX solar grid export",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=None,
        default_entity_id="input_number.immax_solar_grid_export",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_battery_charge",
        name="IMMAX solar battery charge",
        icon="mdi:battery-arrow-up",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=None,
        default_entity_id="input_number.immax_solar_battery_charge",
    ),
    ImmaxProxySensorEntityDescription(
        key="immax_solar_battery_discharge",
        name="IMMAX solar battery discharge",
        icon="mdi:battery-arrow-down",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        option_key=None,
        default_entity_id="input_number.immax_solar_battery_discharge",
    ),
)


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
    elektrum_coordinator = hass.data[DOMAIN][config_entry.entry_id].get(
        "elektrum_coordinator"
    )
    charging_accounts_coordinator = hass.data[DOMAIN][config_entry.entry_id].get(
        "charging_accounts_coordinator"
    )
    entities: list[SensorEntity] = []
    if control is not None:
        entities.extend(
            (
                ZoeNewChargeCommandSensor(control),
                ZoeNewApiLastUpdatedSensor(control),
                ZoeNewRawChargeStatusSensor(control),
                ZoeNewRawPlugStatusSensor(control),
                ZoeNewCostSettingsSensor(config_entry, control),
            )
        )
        entities.extend(
            ZoeNewImmaxProxySensor(config_entry, control, description)
            for description in IMMAX_PROXY_SENSOR_DESCRIPTIONS
        )
        if nordpool_coordinator is not None:
            entities.append(ZoeNordPoolPriceSensor(nordpool_coordinator, control))
        if elektrum_coordinator is not None and nordpool_coordinator is not None:
            entities.extend(
                (
                    ZoeNewElektrumStationSensor(elektrum_coordinator, control),
                    ZoeNewElektrumDrivePriceSensor(elektrum_coordinator, control),
                    ZoeNewEffectiveChargingPriceSensor(
                        elektrum_coordinator,
                        nordpool_coordinator,
                        config_entry,
                        control,
                    ),
                )
            )
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
        if charging_accounts_coordinator is not None:
            entities.append(
                ZoeNewChargingAccountsSensor(
                    charging_accounts_coordinator,
                    control,
                )
            )
    async_add_entities(entities)


class ZoeNewChargingAccountsSensor(CoordinatorEntity, SensorEntity):
    """Expose merged exact-cost transactions from all configured accounts."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:account-cash"
    _attr_name = "Charging accounts"
    _attr_suggested_object_id = "renault_zoe_new_charging_accounts"
    _unrecorded_attributes = frozenset({"transactions"})

    def __init__(
        self,
        coordinator: ChargingAccountsCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_CHARGING_ACCOUNTS
        )
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_charging_accounts".lower()
        )

    @property
    @override
    def native_value(self) -> int:
        """Return the number of unique provider transactions."""
        return int(self.coordinator.data.get("transaction_count", 0))

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose sanitized account status and merged transaction details."""
        return {
            "configured": self.coordinator.data.get("configured", False),
            "account_count": self.coordinator.data.get("account_count", 0),
            "enabled_account_count": self.coordinator.data.get(
                "enabled_account_count", 0
            ),
            "accounts": self.coordinator.data.get("accounts", []),
            "transactions": self.coordinator.data.get("transactions", []),
            "last_fetched": self.coordinator.data.get("fetched_at"),
        }


class ZoeNewCostSettingsSensor(SensorEntity):
    """Expose the configured cost model to dashboards and Pyscript."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:cash-cog"
    _attr_name = "Cost settings"
    _attr_native_unit_of_measurement = "EUR/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_object_id = "renault_zoe_new_cost_settings"

    def __init__(
        self,
        config_entry: ConfigEntry,
        control: ZoeNewChargeControl,
    ) -> None:
        """Initialize the cost settings sensor."""
        self.config_entry = config_entry
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_SMART_CHARGING
        )
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_cost_settings".lower()
        )

    @property
    def settings(self) -> dict[str, float]:
        """Return normalized cost model options."""
        options = self.config_entry.options
        delivery_excl_vat = float(
            options.get(
                CONF_DELIVERY_PRICE_EXCL_VAT,
                DEFAULT_DELIVERY_PRICE_EXCL_VAT,
            )
        )
        vat_percent = float(
            options.get(CONF_ENERGY_VAT_PERCENT, DEFAULT_ENERGY_VAT_PERCENT)
        )
        return {
            "delivery_price_excl_vat_eur_per_kwh": delivery_excl_vat,
            "vat_percent": vat_percent,
            "delivery_price_incl_vat_eur_per_kwh": (
                delivery_excl_vat * (1 + vat_percent / 100)
            ),
            "battery_capacity_kwh": float(
                options.get(
                    CONF_BATTERY_CAPACITY_KWH,
                    DEFAULT_BATTERY_CAPACITY_KWH,
                )
            ),
            "charging_efficiency_percent": float(
                options.get(
                    CONF_CHARGING_EFFICIENCY_PERCENT,
                    DEFAULT_CHARGING_EFFICIENCY_PERCENT,
                )
            ),
            "default_charging_power_kw": float(
                options.get(
                    CONF_DEFAULT_CHARGING_POWER_KW,
                    DEFAULT_DEFAULT_CHARGING_POWER_KW,
                )
            ),
            "fallback_consumption_kwh_per_100km": float(
                options.get(
                    CONF_FALLBACK_CONSUMPTION_KWH_100,
                    DEFAULT_FALLBACK_CONSUMPTION_KWH_100,
                )
            ),
        }

    @property
    def native_value(self) -> float:
        """Return the delivery price including VAT."""
        return round(
            self.settings["delivery_price_incl_vat_eur_per_kwh"],
            7,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose every configurable cost-model value."""
        settings: dict[str, Any] = dict(self.settings)
        settings["charging_efficiency"] = (
            settings["charging_efficiency_percent"] / 100
        )
        settings["dashboard_language"] = self.config_entry.options.get(
            CONF_DASHBOARD_LANGUAGE,
            DEFAULT_DASHBOARD_LANGUAGE,
        )
        settings["immax_feature_enabled"] = self.config_entry.options.get(
            CONF_IMMAX_FEATURE_ENABLED,
            DEFAULT_IMMAX_FEATURE_ENABLED,
        )
        settings["immax_total_load_entity"] = self.config_entry.options.get(
            CONF_IMMAX_TOTAL_LOAD_ENTITY,
            DEFAULT_IMMAX_TOTAL_LOAD_ENTITY,
        )
        settings["elektrum_drive_enabled"] = self.config_entry.options.get(
            CONF_ELEKTRUM_DRIVE_ENABLED,
            DEFAULT_ELEKTRUM_DRIVE_ENABLED,
        )
        settings["elektrum_postpaid_discount_percent"] = (
            self.config_entry.options.get(
                CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
                DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
            )
        )
        return settings


class ZoeNewImmaxProxySensor(SensorEntity):
    """Expose a user-selected source through a stable read-only entity."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset(
        {"today", "tomorrow", "raw_today", "raw_tomorrow"}
    )

    def __init__(
        self,
        config_entry: ConfigEntry,
        control: ZoeNewChargeControl,
        description: ImmaxProxySensorEntityDescription,
    ) -> None:
        """Initialize a configurable source proxy."""
        self.config_entry = config_entry
        self.entity_description = description
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_IMMAX
        )
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_{description.key}".lower()
        )
        self._attr_suggested_object_id = description.key

    @property
    def source_entity_id(self) -> str | None:
        """Return the selected source entity."""
        if self.entity_description.option_key is None:
            return self.entity_description.default_entity_id
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
        """Keep the proxy available so optional-source metadata is retained."""
        return True

    @property
    @override
    def native_value(self) -> float | str | None:
        """Mirror a numeric or textual source state."""
        source = self.source_state
        if source is None or source.state in {STATE_UNAVAILABLE, STATE_UNKNOWN}:
            return None
        try:
            return float(source.state)
        except ValueError:
            return source.state

    @property
    @override
    def native_unit_of_measurement(self) -> str | None:
        """Mirror the source unit."""
        source = self.source_state
        return source.attributes.get("unit_of_measurement") if source else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose source details and planner attributes."""
        source = self.source_state
        attributes = {
            "source_entity_id": self.source_entity_id,
            "configured": self.source_entity_id is not None,
            "source_available": (
                source is not None
                and source.state not in {STATE_UNAVAILABLE, STATE_UNKNOWN}
            ),
        }
        if source is None:
            return attributes
        attributes.update(
            {
                key: value
                for key, value in source.attributes.items()
                if key
                not in {
                    "device_class",
                    "friendly_name",
                    "icon",
                    "state_class",
                    "unit_of_measurement",
                }
            }
        )
        return attributes

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
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_NORDPOOL
        )
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


class _ZoeNewElektrumSensor(CoordinatorEntity, SensorEntity):
    """Base entity for Elektrum Drive station and tariff data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElektrumDriveCoordinator,
        control: ZoeNewChargeControl,
        unique_id_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_CHARGING_ACCOUNTS
        )
        self._attr_unique_id = (
            f"{control.vehicle.details.vin}_{unique_id_suffix}".lower()
        )


class ZoeNewElektrumStationSensor(_ZoeNewElektrumSensor):
    """Expose the Elektrum Drive station nearest to the Zoe."""

    _attr_icon = "mdi:ev-station"
    _attr_name = "Elektrum Drive station"
    _attr_suggested_object_id = "renault_zoe_new_elektrum_drive_station"
    _unrecorded_attributes = frozenset({"connectors"})

    def __init__(
        self,
        coordinator: ElektrumDriveCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        super().__init__(coordinator, control, "zoe_new_elektrum_station")

    @property
    @override
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data.get("enabled", False)
            and self.coordinator.data.get("location_available", False)
        )

    @property
    @override
    def native_value(self) -> str:
        if self.coordinator.data.get("matched"):
            return self.coordinator.data.get("station_name") or "detected"
        return "not_detected"

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.coordinator.data.items()
            if key not in {"price_c_per_kwh", "selected_connector"}
        }


class ZoeNewElektrumDrivePriceSensor(_ZoeNewElektrumSensor):
    """Expose the current connector price including applicable discount."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:ev-station"
    _attr_name = "Elektrum Drive price"
    _attr_native_unit_of_measurement = "c/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_object_id = "renault_zoe_new_elektrum_drive_price"

    def __init__(
        self,
        coordinator: ElektrumDriveCoordinator,
        control: ZoeNewChargeControl,
    ) -> None:
        super().__init__(coordinator, control, "zoe_new_elektrum_drive_price")

    @property
    @override
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data.get("matched", False)
            and self.coordinator.data.get("price_c_per_kwh") is not None
        )

    @property
    @override
    def native_value(self) -> float | None:
        return self.coordinator.data.get("price_c_per_kwh")

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "station_name": data.get("station_name"),
            "station_id": data.get("station_id"),
            "station_address": data.get("station_address"),
            "station_city": data.get("station_city"),
            "distance_m": data.get("distance_m"),
            "partner": data.get("station_partner"),
            "connector_code": data.get("connector_code"),
            "connector_status": data.get("connector_status"),
            "connector_type": data.get("connector_type"),
            "connector_power_kw": data.get("connector_power_kw"),
            "direct_price_c_per_kwh": data.get("direct_price_c_per_kwh"),
            "postpaid_discount_percent": data.get(
                "postpaid_discount_percent"
            ),
            "vat_included": True,
            "source": data.get("price_source"),
            "source_url": data.get("price_url"),
            "last_fetched": data.get("fetched_at"),
        }


class ZoeNewEffectiveChargingPriceSensor(_ZoeNewElektrumSensor):
    """Expose one all-in price for live and completed charging costs."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:cash-sync"
    _attr_name = "Effective charging price"
    _attr_native_unit_of_measurement = "c/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_object_id = "renault_zoe_new_effective_charging_price"

    def __init__(
        self,
        coordinator: ElektrumDriveCoordinator,
        nordpool_coordinator: NordPoolPriceCoordinator,
        config_entry: ConfigEntry,
        control: ZoeNewChargeControl,
    ) -> None:
        super().__init__(coordinator, control, "zoe_new_effective_charging_price")
        self.nordpool_coordinator = nordpool_coordinator
        self.config_entry = config_entry

    @property
    def _price_data(self) -> dict[str, Any]:
        elektrum = self.coordinator.data
        if elektrum.get("matched"):
            return {
                "value": elektrum.get("price_c_per_kwh"),
                "price_source": "elektrum_drive",
                "station_name": elektrum.get("station_name"),
                "station_id": elektrum.get("station_id"),
                "station_address": elektrum.get("station_address"),
                "station_city": elektrum.get("station_city"),
                "station_partner": elektrum.get("station_partner"),
                "connector_code": elektrum.get("connector_code"),
                "connector_status": elektrum.get("connector_status"),
                "direct_price_c_per_kwh": elektrum.get(
                    "direct_price_c_per_kwh"
                ),
                "postpaid_discount_percent": elektrum.get(
                    "postpaid_discount_percent"
                ),
                "source_url": elektrum.get("price_url"),
                "last_fetched": elektrum.get("fetched_at"),
            }

        spot_price = self.nordpool_coordinator.data.get("value")
        if spot_price is None:
            return {"value": None, "price_source": "home_nord_pool"}
        options = self.config_entry.options
        delivery_excl_vat = float(
            options.get(
                CONF_DELIVERY_PRICE_EXCL_VAT,
                DEFAULT_DELIVERY_PRICE_EXCL_VAT,
            )
        )
        vat_percent = float(
            options.get(CONF_ENERGY_VAT_PERCENT, DEFAULT_ENERGY_VAT_PERCENT)
        )
        delivery_cents = delivery_excl_vat * (1 + vat_percent / 100) * 100
        return {
            "value": round(float(spot_price) + delivery_cents, 4),
            "price_source": "home_nord_pool",
            "spot_price_c_per_kwh": float(spot_price),
            "delivery_price_c_per_kwh": round(delivery_cents, 4),
            "nordpool_region": self.nordpool_coordinator.data.get("region"),
            "nordpool_source_entity": self.nordpool_coordinator.data.get(
                "source_entity"
            ),
            "last_fetched": self.nordpool_coordinator.data.get("last_fetched"),
        }

    @property
    @override
    def available(self) -> bool:
        return super().available and self._price_data.get("value") is not None

    @property
    @override
    def native_value(self) -> float | None:
        return self._price_data.get("value")

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self._price_data.items() if key != "value"},
            "all_in": True,
            "vat_included": True,
            "elektrum_station_matched": self.coordinator.data.get(
                "matched", False
            ),
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.nordpool_coordinator.async_add_listener(
                self._handle_nordpool_update
            )
        )

    @callback
    def _handle_nordpool_update(self) -> None:
        self.async_write_ha_state()


class ZoeNewChargeCommandSensor(SensorEntity):
    """Expose accepted and confirmed Renault charge command state."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"
    _attr_name = "Charge command"

    def __init__(self, control: ZoeNewChargeControl) -> None:
        """Initialize the sensor."""
        self.control = control
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_ZOE_API
        )
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
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_ZOE_API
        )


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
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_ZOE_API
        )
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
        self._attr_device_info = source_device_info(
            control.vehicle, SOURCE_ZOE_API
        )
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
