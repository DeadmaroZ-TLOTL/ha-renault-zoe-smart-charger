"""Optional Renault cloud data that is not exposed by Home Assistant core."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .charge_control import ZoeNewChargeControl
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=1)
ACTIVE_CONTRACT_STATES = {"ACTIVE", "CONFIRMED"}


def _contract_data(contract: Any) -> dict[str, Any]:
    """Return recorder-safe contract details without account identifiers."""
    return {
        "type": contract.type,
        "code": contract.code,
        "group": contract.group,
        "duration_months": contract.durationMonths,
        "start_date": contract.startDate,
        "end_date": contract.endDate,
        "status": contract.status,
        "status_label": contract.statusLabel,
        "description": contract.description,
    }


class ZoeNewCloudExtrasCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the working X102VE contracts and cloud-alert endpoints."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        control: ZoeNewChargeControl,
    ) -> None:
        """Initialize the coordinator."""
        self.vehicle = control.vehicle._vehicle
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} cloud extras",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch optional data while preserving the last good response."""
        previous = self.data or {}
        result: dict[str, Any] = {
            "alerts": previous.get("alerts", []),
            "alerts_available": previous.get("alerts_available", False),
            "alerts_error": None,
            "contracts": previous.get("contracts", []),
            "contracts_available": previous.get("contracts_available", False),
            "contracts_error": None,
        }

        alerts_endpoint = (
            f"/commerce/v1/accounts/{self.vehicle.account_id}/vehicles/"
            f"{self.vehicle.vin}/alerts"
        )
        try:
            response = await self.vehicle.session.http_request("GET", alerts_endpoint)
            raw_alerts = response.raw_data.get("data", [])
            result["alerts"] = raw_alerts if isinstance(raw_alerts, list) else []
            result["alerts_available"] = True
        except Exception as err:  # Optional Renault endpoints vary by vehicle.
            result["alerts_error"] = str(err)[:240]
            _LOGGER.debug("Unable to update Zoe cloud alerts: %s", err)

        try:
            response = await self.vehicle.session.get_vehicle_contracts(
                account_id=self.vehicle.account_id,
                vin=self.vehicle.vin,
            )
            result["contracts"] = [
                _contract_data(contract) for contract in response.contractList or []
            ]
            result["contracts_available"] = True
        except Exception as err:  # Preserve warranty data during transient outages.
            result["contracts_error"] = str(err)[:240]
            _LOGGER.debug("Unable to update Zoe contracts: %s", err)

        return result


def active_contracts(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return active or confirmed contracts from coordinator data."""
    return [
        contract
        for contract in data.get("contracts", [])
        if contract.get("status") in ACTIVE_CONTRACT_STATES
    ]


def find_contract(
    data: dict[str, Any], *, code: str | None = None, description: str | None = None
) -> dict[str, Any] | None:
    """Find a contract by stable Renault code or description."""
    for contract in data.get("contracts", []):
        if code is not None and contract.get("code") == code:
            return contract
        if description is not None and contract.get("description") == description:
            return contract
    return None
