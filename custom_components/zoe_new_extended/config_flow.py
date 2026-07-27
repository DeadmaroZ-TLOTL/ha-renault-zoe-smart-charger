"""Config flow for Zoe New Extended."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ALLOW_ANY_LOCATION,
    CONF_ALLOWED_ZONES,
    CONF_IMMAX_BATTERY_CHARGE_ENTITY,
    CONF_IMMAX_BATTERY_DISCHARGE_ENTITY,
    CONF_IMMAX_CHARGER_CURRENT_ENTITY,
    CONF_IMMAX_CHARGER_ENERGY_ENTITY,
    CONF_IMMAX_CHARGER_ONLINE_ENTITY,
    CONF_IMMAX_CHARGER_PROBLEM_ENTITY,
    CONF_IMMAX_CHARGER_STATUS_ENTITY,
    CONF_IMMAX_CHARGER_SWITCH_ENTITY,
    CONF_IMMAX_GRID_EXPORT_ENTITY,
    CONF_IMMAX_NORDPOOL_PRICE_ENTITY,
    CONF_IMMAX_POWER_A_ENTITY,
    CONF_IMMAX_POWER_B_ENTITY,
    CONF_IMMAX_POWER_C_ENTITY,
    CONF_IMMAX_VEHICLE_SOC_ENTITY,
    CONF_IMMAX_VOLTAGE_A_ENTITY,
    CONF_IMMAX_VOLTAGE_B_ENTITY,
    CONF_IMMAX_VOLTAGE_C_ENTITY,
    CONF_LOCATION_CONTROL_ENABLED,
    CONF_NORDPOOL_AREA,
    DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY,
    DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY,
    DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY,
    DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY,
    DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY,
    DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY,
    DEFAULT_IMMAX_CHARGER_STATUS_ENTITY,
    DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY,
    DEFAULT_IMMAX_GRID_EXPORT_ENTITY,
    DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY,
    DEFAULT_IMMAX_POWER_A_ENTITY,
    DEFAULT_IMMAX_POWER_B_ENTITY,
    DEFAULT_IMMAX_POWER_C_ENTITY,
    DEFAULT_IMMAX_VEHICLE_SOC_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_A_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_B_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_C_ENTITY,
    DEFAULT_NORDPOOL_AREA,
    DOMAIN,
    NORDPOOL_AREAS,
)

IMMAX_ENTITY_FIELDS = (
    (CONF_IMMAX_CHARGER_SWITCH_ENTITY, DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY, "switch"),
    (CONF_IMMAX_CHARGER_CURRENT_ENTITY, DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY, "number"),
    (CONF_IMMAX_CHARGER_STATUS_ENTITY, DEFAULT_IMMAX_CHARGER_STATUS_ENTITY, "sensor"),
    (CONF_IMMAX_CHARGER_ONLINE_ENTITY, DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY, "switch"),
    (
        CONF_IMMAX_CHARGER_PROBLEM_ENTITY,
        DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY,
        "binary_sensor",
    ),
    (CONF_IMMAX_POWER_A_ENTITY, DEFAULT_IMMAX_POWER_A_ENTITY, "sensor"),
    (CONF_IMMAX_POWER_B_ENTITY, DEFAULT_IMMAX_POWER_B_ENTITY, "sensor"),
    (CONF_IMMAX_POWER_C_ENTITY, DEFAULT_IMMAX_POWER_C_ENTITY, "sensor"),
    (CONF_IMMAX_VOLTAGE_A_ENTITY, DEFAULT_IMMAX_VOLTAGE_A_ENTITY, "sensor"),
    (CONF_IMMAX_VOLTAGE_B_ENTITY, DEFAULT_IMMAX_VOLTAGE_B_ENTITY, "sensor"),
    (CONF_IMMAX_VOLTAGE_C_ENTITY, DEFAULT_IMMAX_VOLTAGE_C_ENTITY, "sensor"),
    (CONF_IMMAX_CHARGER_ENERGY_ENTITY, DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY, "sensor"),
    (CONF_IMMAX_GRID_EXPORT_ENTITY, DEFAULT_IMMAX_GRID_EXPORT_ENTITY, "sensor"),
    (
        CONF_IMMAX_BATTERY_CHARGE_ENTITY,
        DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY,
        "sensor",
    ),
    (
        CONF_IMMAX_BATTERY_DISCHARGE_ENTITY,
        DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY,
        "sensor",
    ),
    (CONF_IMMAX_VEHICLE_SOC_ENTITY, DEFAULT_IMMAX_VEHICLE_SOC_ENTITY, "sensor"),
    (
        CONF_IMMAX_NORDPOOL_PRICE_ENTITY,
        DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY,
        "sensor",
    ),
)


class ZoeNewExtendedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single Zoe New Extended config entry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the integration without requiring user input."""
        await self.async_set_unique_id("renault_zoe_new_extended")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Renault Zoe New", data={})

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the smart charging options flow."""
        return ZoeNewExtendedOptionsFlow()


class ZoeNewExtendedOptionsFlow(config_entries.OptionsFlow):
    """Configure smart charging and its selected Home Assistant entities."""

    async def async_step_init(self, user_input=None):
        """Show the settings categories."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["smart_charging", "immax_entities"],
        )

    def _create_merged_entry(self, user_input):
        """Save one settings page without dropping options from another."""
        options = dict(self.config_entry.options)
        options.update(user_input)
        return self.async_create_entry(title="", data=options)

    async def async_step_smart_charging(self, user_input=None):
        """Configure allowed charging zones and Nord Pool area."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        allowed_zones = self.config_entry.options.get(CONF_ALLOWED_ZONES, [])
        location_control_enabled = self.config_entry.options.get(
            CONF_LOCATION_CONTROL_ENABLED, True
        )
        allow_any_location = self.config_entry.options.get(
            CONF_ALLOW_ANY_LOCATION, True
        )
        nordpool_area = self.config_entry.options.get(
            CONF_NORDPOOL_AREA, DEFAULT_NORDPOOL_AREA
        )
        return self.async_show_form(
            step_id="smart_charging",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NORDPOOL_AREA, default=nordpool_area
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": area, "label": f"{name} ({area})"}
                                for area, (name, _vat) in NORDPOOL_AREAS.items()
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_LOCATION_CONTROL_ENABLED,
                        default=location_control_enabled,
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_ALLOW_ANY_LOCATION,
                        default=allow_any_location,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_ALLOWED_ZONES, default=allowed_zones
                    ): EntitySelector(
                        EntitySelectorConfig(domain="zone", multiple=True)
                    ),
                }
            ),
        )

    async def async_step_immax_entities(self, user_input=None):
        """Configure the source entities used by the IMMAX controller."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        return self.async_show_form(
            step_id="immax_entities",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        key,
                        default=self.config_entry.options.get(key, default),
                    ): EntitySelector(EntitySelectorConfig(domain=domain))
                    for key, default, domain in IMMAX_ENTITY_FIELDS
                }
            ),
        )
