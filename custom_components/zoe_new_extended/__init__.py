"""Attach custom Zoe sensors to the Renault Zoe New device."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from .charge_control import ZoeNewChargeControl, find_zoe_new
from .const import (
    API_ENTITY_IDS,
    CONF_IMMAX_AI_ADVISOR_ENABLED,
    CONF_IMMAX_AI_ADVISOR_INTERVAL,
    CONF_IMMAX_AI_CURRENT_CAP,
    CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT,
    CONF_IMMAX_BATTERY_SOC_STOP_LIMIT,
    CONF_IMMAX_CHARGE_TARGET_PERCENTAGE,
    CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED,
    CONF_IMMAX_DELAY_PERIOD,
    CONF_IMMAX_ENERGY_TO_ADD,
    CONF_IMMAX_FEATURE_ENABLED,
    CONF_IMMAX_MAX_ENERGY_PRICE,
    CONF_IMMAX_MAX_PRICE_ENABLED,
    CONF_IMMAX_NORDPOOL_CURRENT,
    CONF_IMMAX_PLANNING_POWER,
    CONF_IMMAX_SMART_CHARGING_MODE,
    CONF_IMMAX_SOLAR_MAX_POWER,
    CONF_IMMAX_SOLAR_MIN_POWER,
    CONF_IMMAX_SOLAR_PHASE_MODE,
    CONF_IMMAX_SOLAR_RESERVE_POWER,
    CONF_IMMAX_TOTAL_POWER_LIMIT,
    CONF_ZOE_CHARGE_RANGE_TARGET_KM,
    CONF_ZOE_CHARGE_TARGET_MODE,
    CONF_ZOE_CHARGE_TARGET_PERCENT,
    CONF_ZOE_MAX_ENERGY_PRICE,
    CONF_ZOE_MAX_PRICE_ENABLED,
    CONF_ZOE_SMART_CHARGING_ENABLED,
    DEFAULT_IMMAX_FEATURE_ENABLED,
    DOMAIN,
    TARGET_ENTITY_ID,
    ZOE_ENTITY_PREFIX,
)
from .extras import ZoeNewCloudExtrasCoordinator
from .nordpool import NordPoolPriceCoordinator

RETRY_SECONDS = 15
PLATFORMS = (
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
)

PRESERVED_SWITCH_UNIQUE_ID_SUFFIXES = (
    "_immax_charging",
    "_smart_charging_any_location",
    "_smart_charging_location_control",
)

IMMAX_SELECT_OPTION_ENTITIES = {
    CONF_IMMAX_SMART_CHARGING_MODE: "input_select.immax_smart_charging_mode",
    CONF_IMMAX_SOLAR_PHASE_MODE: "input_select.immax_solar_phase_mode",
}

ZOE_SELECT_OPTION_ENTITIES = {
    CONF_ZOE_CHARGE_TARGET_MODE: "input_select.zoe_charge_target_mode",
}

IMMAX_BOOLEAN_OPTION_ENTITIES = {
    CONF_IMMAX_FEATURE_ENABLED: "input_boolean.immax_feature_enabled",
    CONF_IMMAX_MAX_PRICE_ENABLED: "input_boolean.immax_max_price_enabled",
    CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED: (
        "input_boolean.immax_charge_to_percentage_enabled"
    ),
    CONF_IMMAX_AI_ADVISOR_ENABLED: "input_boolean.immax_ai_advisor_enabled",
}

ZOE_BOOLEAN_OPTION_ENTITIES = {
    CONF_ZOE_SMART_CHARGING_ENABLED: "input_boolean.zoe_smart_charging",
    CONF_ZOE_MAX_PRICE_ENABLED: "input_boolean.zoe_max_price_enabled",
}

IMMAX_NUMBER_OPTION_ENTITIES = {
    CONF_IMMAX_DELAY_PERIOD: "input_number.immax_delay_period",
    CONF_IMMAX_TOTAL_POWER_LIMIT: "input_number.immax_total_power_limit",
    CONF_IMMAX_BATTERY_SOC_STOP_LIMIT: (
        "input_number.immax_battery_soc_stop_limit"
    ),
    CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT: (
        "input_number.immax_battery_soc_resume_limit"
    ),
    CONF_IMMAX_AI_ADVISOR_INTERVAL: "input_number.immax_ai_advisor_interval",
    CONF_IMMAX_AI_CURRENT_CAP: "input_number.immax_ai_current_cap",
    CONF_IMMAX_MAX_ENERGY_PRICE: "input_number.immax_max_energy_price",
    CONF_IMMAX_ENERGY_TO_ADD: "input_number.immax_energy_to_add",
    CONF_IMMAX_CHARGE_TARGET_PERCENTAGE: (
        "input_number.immax_charge_target_percentage"
    ),
    CONF_IMMAX_NORDPOOL_CURRENT: "input_number.immax_nordpool_current",
    CONF_IMMAX_PLANNING_POWER: "input_number.immax_planning_power",
    CONF_IMMAX_SOLAR_RESERVE_POWER: "input_number.immax_solar_reserve_power",
    CONF_IMMAX_SOLAR_MIN_POWER: "input_number.immax_solar_min_power",
    CONF_IMMAX_SOLAR_MAX_POWER: "input_number.immax_solar_max_power",
}

ZOE_NUMBER_OPTION_ENTITIES = {
    CONF_ZOE_CHARGE_TARGET_PERCENT: "input_number.zoe_charge_target",
    CONF_ZOE_CHARGE_RANGE_TARGET_KM: "input_number.zoe_charge_range_target",
    CONF_ZOE_MAX_ENERGY_PRICE: "input_number.zoe_max_energy_price",
}


async def _async_sync_charging_setpoints(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Apply saved integration options to existing charging helpers."""
    options = entry.options
    for key, entity_id in (
        IMMAX_SELECT_OPTION_ENTITIES | ZOE_SELECT_OPTION_ENTITIES
    ).items():
        current_state = hass.states.get(entity_id)
        if key not in options or current_state is None:
            continue
        option = str(options[key])
        if current_state.state == option:
            continue
        await hass.services.async_call(
            "input_select",
            "select_option",
            {"entity_id": entity_id, "option": option},
            blocking=True,
        )

    for key, entity_id in (
        IMMAX_BOOLEAN_OPTION_ENTITIES | ZOE_BOOLEAN_OPTION_ENTITIES
    ).items():
        current_state = hass.states.get(entity_id)
        if current_state is None:
            continue
        if key not in options:
            if key != CONF_IMMAX_FEATURE_ENABLED:
                continue
            turn_on = DEFAULT_IMMAX_FEATURE_ENABLED
        else:
            turn_on = bool(options[key])
        if (current_state.state == "on") == turn_on:
            continue
        await hass.services.async_call(
            "input_boolean",
            "turn_on" if turn_on else "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )

    immax_enabled = bool(
        options.get(CONF_IMMAX_FEATURE_ENABLED, DEFAULT_IMMAX_FEATURE_ENABLED)
    )
    immax_automations = [
        state.entity_id
        for state in hass.states.async_all("automation")
        if state.entity_id.startswith("automation.immax_")
    ]
    if immax_automations:
        service_data: dict[str, object] = {"entity_id": immax_automations}
        if not immax_enabled:
            service_data["stop_actions"] = True
        await hass.services.async_call(
            "automation",
            "turn_on" if immax_enabled else "turn_off",
            service_data,
            blocking=True,
        )

    for key, entity_id in (
        IMMAX_NUMBER_OPTION_ENTITIES | ZOE_NUMBER_OPTION_ENTITIES
    ).items():
        current_state = hass.states.get(entity_id)
        if key not in options or current_state is None:
            continue
        value = float(options[key])
        try:
            current_value = float(current_state.state)
        except (TypeError, ValueError):
            current_value = None
        if current_value is not None and abs(current_value - value) < 0.0001:
            continue
        await hass.services.async_call(
            "input_number",
            "set_value",
            {"entity_id": entity_id, "value": value},
            blocking=True,
        )


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload options and refresh the derived charging-cost history."""
    await hass.config_entries.async_reload(entry.entry_id)
    if hass.services.has_service("pyscript", "zoe_charge_sessions_update"):
        hass.async_create_task(
            hass.services.async_call(
                "pyscript",
                "zoe_charge_sessions_update",
                blocking=False,
            )
        )


def _is_managed_entity(entity_id: str) -> bool:
    return entity_id in API_ENTITY_IDS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Keep the custom Zoe sensors attached to the active Zoe New device."""
    vehicle = find_zoe_new(hass)
    if vehicle is None:
        raise ConfigEntryNotReady("Renault Zoe New is not loaded yet")

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    retry_cancel: Callable[[], None] | None = None
    reconcile_cancel: Callable[[], None] | None = None
    reconciling = False
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    for registry_entry in tuple(entity_registry.entities.values()):
        if (
            registry_entry.config_entry_id == entry.entry_id
            and registry_entry.entity_id.startswith("switch.")
            and not registry_entry.unique_id.endswith(
                PRESERVED_SWITCH_UNIQUE_ID_SUFFIXES
            )
        ):
            entity_registry.async_remove(registry_entry.entity_id)

    @callback
    def schedule_retry() -> None:
        nonlocal retry_cancel
        if retry_cancel is not None:
            return

        @callback
        def retry(_now: datetime) -> None:
            nonlocal retry_cancel
            retry_cancel = None
            reconcile()

        retry_cancel = async_call_later(hass, RETRY_SECONDS, retry)

    @callback
    def reconcile() -> None:
        nonlocal reconciling
        if reconciling:
            return

        target_entity = entity_registry.async_get(TARGET_ENTITY_ID)
        if (
            target_entity is None
            or target_entity.platform != "renault"
            or target_entity.device_id is None
        ):
            schedule_retry()
            return

        target_device = device_registry.async_get(target_entity.device_id)
        if (
            target_device is None
            or target_device.manufacturer != "Renault"
            or target_device.model != "Zoe"
        ):
            schedule_retry()
            return

        reconciling = True
        try:
            for registry_entry in tuple(entity_registry.entities.values()):
                if (
                    registry_entry.entity_id.startswith(ZOE_ENTITY_PREFIX)
                    and not _is_managed_entity(registry_entry.entity_id)
                    and registry_entry.device_id == target_device.id
                ):
                    entity_registry.async_update_entity(
                        registry_entry.entity_id,
                        device_id=None,
                    )
                    continue
                if not _is_managed_entity(registry_entry.entity_id):
                    continue
                if registry_entry.device_id == target_device.id:
                    continue
                entity_registry.async_update_entity(
                    registry_entry.entity_id,
                    device_id=target_device.id,
                )
        finally:
            reconciling = False

    @callback
    def schedule_reconcile() -> None:
        """Coalesce registry bursts caused by platform setup and device moves."""
        nonlocal reconcile_cancel
        if reconcile_cancel is not None:
            return

        @callback
        def run_reconcile(_now: datetime) -> None:
            nonlocal reconcile_cancel
            reconcile_cancel = None
            reconcile()

        reconcile_cancel = async_call_later(hass, 0.25, run_reconcile)

    @callback
    def registry_updated(event: Event) -> None:
        entity_id = event.data.get("entity_id", "")
        if entity_id == TARGET_ENTITY_ID or entity_id.startswith(ZOE_ENTITY_PREFIX):
            schedule_reconcile()

    unsubscribe_registry = hass.bus.async_listen(
        er.EVENT_ENTITY_REGISTRY_UPDATED, registry_updated
    )
    reconcile()

    charge_control = ZoeNewChargeControl(hass, vehicle)
    nordpool_coordinator = NordPoolPriceCoordinator(hass, entry)
    await nordpool_coordinator.async_config_entry_first_refresh()
    extras_coordinator = ZoeNewCloudExtrasCoordinator(hass, entry, charge_control)
    await extras_coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "unsubscribe_registry": unsubscribe_registry,
        "cancel_retry": lambda: retry_cancel() if retry_cancel else None,
        "cancel_reconcile": (
            lambda: reconcile_cancel() if reconcile_cancel else None
        ),
        "charge_control": charge_control,
        "nordpool_coordinator": nordpool_coordinator,
        "extras_coordinator": extras_coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_sync_charging_setpoints(hass, entry)

    @callback
    def sync_after_automation_setup(_now: datetime) -> None:
        """Repeat once after YAML helpers and automations have finished loading."""
        hass.async_create_task(_async_sync_charging_setpoints(hass, entry))

    hass.data[DOMAIN][entry.entry_id]["cancel_setpoint_sync"] = async_call_later(
        hass,
        10,
        sync_after_automation_setup,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload registry listeners."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime:
        if runtime["charge_control"] is not None:
            runtime["charge_control"].restore()
        runtime["unsubscribe_registry"]()
        runtime["cancel_retry"]()
        runtime["cancel_reconcile"]()
        runtime["cancel_setpoint_sync"]()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Detach managed sensors if the helper integration is removed."""
    entity_registry = er.async_get(hass)
    for registry_entry in tuple(entity_registry.entities.values()):
        if registry_entry.entity_id.startswith(
            ZOE_ENTITY_PREFIX
        ) and _is_managed_entity(registry_entry.entity_id):
            entity_registry.async_update_entity(
                registry_entry.entity_id,
                device_id=None,
            )
