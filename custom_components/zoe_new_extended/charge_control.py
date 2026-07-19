"""Working X102VE charge commands for the current MyRenault API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from renault_api.exceptions import RenaultException
from renault_api.kamereon import schemas
from renault_api.kamereon.enums import ChargeState
from renault_api.kamereon.models import (
    EndpointDefinition,
    KamereonVehicleChargingStartActionData,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

MODEL_CODE = "X102VE"
STOP_DELAY = timedelta(hours=24)
CONFIRM_DELAYS = (10, 20, 30, 60, 60)
KCM_CHARGE_START = EndpointDefinition("/kcm/v1/vehicles/{vin}/charge/start", mode="kcm")


def find_zoe_new(hass: HomeAssistant) -> Any | None:
    """Return the active Zoe phase 2 proxy."""
    for renault_entry in hass.config_entries.async_entries("renault"):
        if renault_entry.state is not ConfigEntryState.LOADED:
            continue
        runtime = renault_entry.runtime_data
        if runtime is None:
            continue
        for vehicle in runtime.vehicles.values():
            if vehicle.details.get_model_code() == MODEL_CODE:
                return vehicle
    return None


class ZoeNewChargeControl:
    """Patch the broken core buttons with the commands used by MyRenault."""

    def __init__(self, hass: HomeAssistant, vehicle: Any) -> None:
        """Initialize and patch the existing Renault vehicle proxy."""
        self.hass = hass
        self.vehicle = vehicle
        self._original_start = vehicle.set_charge_start
        self._original_stop = vehicle.set_charge_stop
        self._listeners: set[Callable[[], None]] = set()
        self._monitor_task: asyncio.Task[None] | None = None
        self.state = "idle"
        self.last_command: str | None = None
        self.last_command_at: str | None = None
        self.last_command_id: str | None = None
        self.last_vehicle_state: str | None = None
        self.last_error: str | None = None
        self.delayed_until: str | None = None

        previous = getattr(vehicle, "_zoe_new_extended_charge_control", None)
        if previous is not None:
            previous.restore()
        vehicle.set_charge_start = self.async_start
        vehicle.set_charge_stop = self.async_stop
        vehicle._zoe_new_extended_charge_control = self

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener."""
        self._listeners.add(listener)

        @callback
        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe

    @callback
    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def _payload(self, when: datetime | None = None) -> dict[str, Any]:
        attributes: dict[str, Any] = {"action": "start"}
        if when is not None:
            attributes["startDateTime"] = when.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:00.000Z"
            )
        return {
            "data": {
                "type": "ChargingStart",
                "attributes": attributes,
            }
        }

    async def async_start(
        self, when: datetime | None = None
    ) -> KamereonVehicleChargingStartActionData:
        """Start now, or use Renault's native delayed start when requested."""
        command = "start" if when is None else "delay"
        return await self._async_send(command, when)

    async def async_stop(self) -> KamereonVehicleChargingStartActionData:
        """Stop charging by moving the native delayed start 24 hours ahead."""
        return await self._async_send("stop", datetime.now(timezone.utc) + STOP_DELAY)

    async def _async_send(
        self, command: str, when: datetime | None
    ) -> KamereonVehicleChargingStartActionData:
        self.last_command = command
        self.last_command_at = datetime.now(timezone.utc).isoformat()
        self.last_command_id = None
        self.last_error = None
        self.delayed_until = when.isoformat() if command == "stop" and when else None
        self.state = "starting" if command == "start" else "stopping"
        self._notify()

        try:
            response = await self.vehicle._vehicle._set_vehicle_data(
                KCM_CHARGE_START, self._payload(when)
            )
        except RenaultException as err:
            self.state = "error"
            self.last_error = str(err)
            self._notify()
            raise HomeAssistantError(f"Renault charge command failed: {err}") from err

        data = response.raw_data.get("data", {})
        self.last_command_id = data.get("id")
        self._start_confirmation(command)
        return cast(
            KamereonVehicleChargingStartActionData,
            response.get_attributes(
                schemas.KamereonVehicleChargingStartActionDataSchema
            ),
        )

    @callback
    def _start_confirmation(self, command: str) -> None:
        if self._monitor_task is not None:
            self._monitor_task.cancel()
        self._monitor_task = self.hass.async_create_task(
            self._async_confirm(command),
            f"Confirm Zoe New {command} command",
        )

    async def _async_confirm(self, command: str) -> None:
        coordinator = self.vehicle.coordinators.get("battery")
        if coordinator is None:
            self.state = "accepted"
            self._notify()
            return

        try:
            for delay in CONFIRM_DELAYS:
                await asyncio.sleep(delay)
                try:
                    await coordinator.async_request_refresh()
                except Exception as err:  # Renault status polling is best-effort.
                    self.last_error = str(err)
                    self._notify()
                    continue

                charge_state = coordinator.data.get_charging_status()
                self.last_vehicle_state = (
                    charge_state.name.lower() if charge_state is not None else None
                )
                self._notify()
                if (
                    command == "start"
                    and charge_state == ChargeState.CHARGE_IN_PROGRESS
                ):
                    self.state = "charging"
                    self.last_error = None
                    self._notify()
                    return
                if (
                    command != "start"
                    and charge_state != ChargeState.CHARGE_IN_PROGRESS
                ):
                    self.state = "stopped" if command == "stop" else "scheduled"
                    self.last_error = None
                    self._notify()
                    return

            self.state = "timeout"
            self._notify()
        except asyncio.CancelledError:
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostics for the command sensor."""
        return {
            "last_command": self.last_command,
            "last_command_at": self.last_command_at,
            "last_command_id": self.last_command_id,
            "last_vehicle_state": self.last_vehicle_state,
            "last_error": self.last_error,
            "delayed_until": self.delayed_until,
        }

    @callback
    def restore(self) -> None:
        """Restore the original proxy methods and stop monitoring."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            self._monitor_task = None
        self.vehicle.set_charge_start = self._original_start
        self.vehicle.set_charge_stop = self._original_stop
        if getattr(self.vehicle, "_zoe_new_extended_charge_control", None) is self:
            delattr(self.vehicle, "_zoe_new_extended_charge_control")
