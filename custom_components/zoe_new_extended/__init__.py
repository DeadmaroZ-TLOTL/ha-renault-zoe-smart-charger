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
    DOMAIN,
    TARGET_ENTITY_ID,
    ZOE_ENTITY_PREFIX,
)

RETRY_SECONDS = 15
PLATFORMS = (
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload location settings after options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


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
    reconciling = False
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

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
    def registry_updated(event: Event) -> None:
        entity_id = event.data.get("entity_id", "")
        if entity_id == TARGET_ENTITY_ID or entity_id.startswith(ZOE_ENTITY_PREFIX):
            reconcile()

    unsubscribe_registry = hass.bus.async_listen(
        er.EVENT_ENTITY_REGISTRY_UPDATED, registry_updated
    )
    reconcile()

    charge_control = ZoeNewChargeControl(hass, vehicle)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "unsubscribe_registry": unsubscribe_registry,
        "cancel_retry": lambda: retry_cancel() if retry_cancel else None,
        "charge_control": charge_control,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
