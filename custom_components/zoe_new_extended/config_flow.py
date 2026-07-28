"""Config flow for Zoe New Extended."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ALLOW_ANY_LOCATION,
    CONF_ALLOWED_ZONES,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_CHARGING_EFFICIENCY_PERCENT,
    CONF_DASHBOARD_LANGUAGE,
    CONF_DEFAULT_CHARGING_POWER_KW,
    CONF_DELIVERY_PRICE_EXCL_VAT,
    CONF_ENERGY_VAT_PERCENT,
    CONF_FALLBACK_CONSUMPTION_KWH_100,
    CONF_IMMAX_BATTERY_CHARGE_ENTITY,
    CONF_IMMAX_BATTERY_DISCHARGE_ENTITY,
    CONF_IMMAX_CHARGER_CURRENT_ENTITY,
    CONF_IMMAX_CHARGER_ENERGY_ENTITY,
    CONF_IMMAX_CHARGER_ONLINE_ENTITY,
    CONF_IMMAX_CHARGER_PROBLEM_ENTITY,
    CONF_IMMAX_CHARGER_STATUS_ENTITY,
    CONF_IMMAX_CHARGER_SWITCH_ENTITY,
    CONF_IMMAX_CURRENT_A_ENTITY,
    CONF_IMMAX_CURRENT_B_ENTITY,
    CONF_IMMAX_CURRENT_C_ENTITY,
    CONF_IMMAX_GRID_EXPORT_ENTITY,
    CONF_IMMAX_NORDPOOL_PRICE_ENTITY,
    CONF_IMMAX_POWER_A_ENTITY,
    CONF_IMMAX_POWER_B_ENTITY,
    CONF_IMMAX_POWER_C_ENTITY,
    CONF_IMMAX_SOLAR_POWER_ENTITY,
    CONF_IMMAX_VEHICLE_SOC_ENTITY,
    CONF_IMMAX_VOLTAGE_A_ENTITY,
    CONF_IMMAX_VOLTAGE_B_ENTITY,
    CONF_IMMAX_VOLTAGE_C_ENTITY,
    CONF_IMMAX_AI_ADVISOR_ENABLED,
    CONF_IMMAX_AI_ADVISOR_INTERVAL,
    CONF_IMMAX_AI_CURRENT_CAP,
    CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT,
    CONF_IMMAX_BATTERY_SOC_STOP_LIMIT,
    CONF_IMMAX_CHARGE_TARGET_PERCENTAGE,
    CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED,
    CONF_IMMAX_DELAY_PERIOD,
    CONF_IMMAX_ENERGY_TO_ADD,
    CONF_IMMAX_MAX_ENERGY_PRICE,
    CONF_IMMAX_MAX_PRICE_ENABLED,
    CONF_IMMAX_NORDPOOL_CURRENT,
    CONF_IMMAX_PLANNING_POWER,
    CONF_IMMAX_SMART_CHARGING_MODE,
    CONF_IMMAX_SOLAR_MAX_POWER,
    CONF_IMMAX_SOLAR_MIN_POWER,
    CONF_IMMAX_SOLAR_PHASE_MODE,
    CONF_IMMAX_SOLAR_RESERVE_POWER,
    CONF_IMMAX_TOTAL_LOAD_ENTITY,
    CONF_IMMAX_TOTAL_POWER_LIMIT,
    CONF_LOCATION_CONTROL_ENABLED,
    CONF_NORDPOOL_AREA,
    CONF_ZOE_CHARGE_RANGE_TARGET_KM,
    CONF_ZOE_CHARGE_TARGET_MODE,
    CONF_ZOE_CHARGE_TARGET_PERCENT,
    CONF_ZOE_MAX_ENERGY_PRICE,
    CONF_ZOE_MAX_PRICE_ENABLED,
    CONF_ZOE_SMART_CHARGING_ENABLED,
    DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY,
    DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY,
    DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY,
    DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY,
    DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY,
    DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY,
    DEFAULT_IMMAX_CHARGER_STATUS_ENTITY,
    DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY,
    DEFAULT_IMMAX_CURRENT_A_ENTITY,
    DEFAULT_IMMAX_CURRENT_B_ENTITY,
    DEFAULT_IMMAX_CURRENT_C_ENTITY,
    DEFAULT_IMMAX_GRID_EXPORT_ENTITY,
    DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY,
    DEFAULT_IMMAX_POWER_A_ENTITY,
    DEFAULT_IMMAX_POWER_B_ENTITY,
    DEFAULT_IMMAX_POWER_C_ENTITY,
    DEFAULT_IMMAX_SOLAR_POWER_ENTITY,
    DEFAULT_IMMAX_VEHICLE_SOC_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_A_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_B_ENTITY,
    DEFAULT_IMMAX_VOLTAGE_C_ENTITY,
    DEFAULT_IMMAX_AI_ADVISOR_ENABLED,
    DEFAULT_IMMAX_AI_ADVISOR_INTERVAL,
    DEFAULT_IMMAX_AI_CURRENT_CAP,
    DEFAULT_IMMAX_BATTERY_SOC_RESUME_LIMIT,
    DEFAULT_IMMAX_BATTERY_SOC_STOP_LIMIT,
    DEFAULT_IMMAX_CHARGE_TARGET_PERCENTAGE,
    DEFAULT_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED,
    DEFAULT_IMMAX_DELAY_PERIOD,
    DEFAULT_IMMAX_ENERGY_TO_ADD,
    DEFAULT_IMMAX_MAX_ENERGY_PRICE,
    DEFAULT_IMMAX_MAX_PRICE_ENABLED,
    DEFAULT_IMMAX_NORDPOOL_CURRENT,
    DEFAULT_IMMAX_PLANNING_POWER,
    DEFAULT_IMMAX_SMART_CHARGING_MODE,
    DEFAULT_IMMAX_SOLAR_MAX_POWER,
    DEFAULT_IMMAX_SOLAR_MIN_POWER,
    DEFAULT_IMMAX_SOLAR_PHASE_MODE,
    DEFAULT_IMMAX_SOLAR_RESERVE_POWER,
    DEFAULT_IMMAX_TOTAL_LOAD_ENTITY,
    DEFAULT_IMMAX_TOTAL_POWER_LIMIT,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_CHARGING_EFFICIENCY_PERCENT,
    DEFAULT_DASHBOARD_LANGUAGE,
    DEFAULT_DEFAULT_CHARGING_POWER_KW,
    DEFAULT_DELIVERY_PRICE_EXCL_VAT,
    DEFAULT_ENERGY_VAT_PERCENT,
    DEFAULT_FALLBACK_CONSUMPTION_KWH_100,
    DEFAULT_NORDPOOL_AREA,
    DEFAULT_ZOE_CHARGE_RANGE_TARGET_KM,
    DEFAULT_ZOE_CHARGE_TARGET_MODE,
    DEFAULT_ZOE_CHARGE_TARGET_PERCENT,
    DEFAULT_ZOE_MAX_ENERGY_PRICE,
    DEFAULT_ZOE_MAX_PRICE_ENABLED,
    DEFAULT_ZOE_SMART_CHARGING_ENABLED,
    DOMAIN,
    NORDPOOL_AREAS,
)

IMMAX_REQUIRED_ENTITY_FIELDS = (
    (CONF_IMMAX_CHARGER_SWITCH_ENTITY, DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY, "switch"),
    (CONF_IMMAX_CHARGER_CURRENT_ENTITY, DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY, "number"),
    (CONF_IMMAX_TOTAL_LOAD_ENTITY, DEFAULT_IMMAX_TOTAL_LOAD_ENTITY, "sensor"),
)

IMMAX_OPTIONAL_ENTITY_FIELDS = (
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
    (CONF_IMMAX_CURRENT_A_ENTITY, DEFAULT_IMMAX_CURRENT_A_ENTITY, "sensor"),
    (CONF_IMMAX_CURRENT_B_ENTITY, DEFAULT_IMMAX_CURRENT_B_ENTITY, "sensor"),
    (CONF_IMMAX_CURRENT_C_ENTITY, DEFAULT_IMMAX_CURRENT_C_ENTITY, "sensor"),
    (CONF_IMMAX_VOLTAGE_A_ENTITY, DEFAULT_IMMAX_VOLTAGE_A_ENTITY, "sensor"),
    (CONF_IMMAX_VOLTAGE_B_ENTITY, DEFAULT_IMMAX_VOLTAGE_B_ENTITY, "sensor"),
    (CONF_IMMAX_VOLTAGE_C_ENTITY, DEFAULT_IMMAX_VOLTAGE_C_ENTITY, "sensor"),
    (CONF_IMMAX_CHARGER_ENERGY_ENTITY, DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY, "sensor"),
    (
        CONF_IMMAX_SOLAR_POWER_ENTITY,
        DEFAULT_IMMAX_SOLAR_POWER_ENTITY,
        "sensor",
    ),
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

    def _option_or_helper(self, key, entity_id, default):
        """Return a saved option, otherwise preserve the current helper value."""
        if key in self.config_entry.options:
            return self.config_entry.options[key]

        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable"}:
            return default
        if isinstance(default, bool):
            return state.state == "on"
        if isinstance(default, float):
            try:
                return float(state.state)
            except (TypeError, ValueError):
                return default
        return state.state

    async def async_step_init(self, user_input=None):
        """Show the settings categories."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "dashboard",
                "smart_charging",
                "cost_model",
                "immax_setpoints",
                "immax_entities",
            ],
        )

    async def async_step_dashboard(self, user_input=None):
        """Configure the shared dashboard language."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        language = self.config_entry.options.get(
            CONF_DASHBOARD_LANGUAGE,
            DEFAULT_DASHBOARD_LANGUAGE,
        )
        return self.async_show_form(
            step_id="dashboard",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DASHBOARD_LANGUAGE,
                        default=language,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "lv", "label": "Latviešu"},
                                {"value": "en", "label": "English"},
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    def _create_merged_entry(self, user_input, *, clear_missing=()):
        """Save one settings page without dropping options from another."""
        options = dict(self.config_entry.options)
        options.update(user_input)
        for key in clear_missing:
            options[key] = user_input.get(key) or ""
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
        smart_charging_enabled = self._option_or_helper(
            CONF_ZOE_SMART_CHARGING_ENABLED,
            "input_boolean.zoe_smart_charging",
            DEFAULT_ZOE_SMART_CHARGING_ENABLED,
        )
        max_price_enabled = self._option_or_helper(
            CONF_ZOE_MAX_PRICE_ENABLED,
            "input_boolean.zoe_max_price_enabled",
            DEFAULT_ZOE_MAX_PRICE_ENABLED,
        )
        target_mode = self._option_or_helper(
            CONF_ZOE_CHARGE_TARGET_MODE,
            "input_select.zoe_charge_target_mode",
            DEFAULT_ZOE_CHARGE_TARGET_MODE,
        )
        target_percent = self._option_or_helper(
            CONF_ZOE_CHARGE_TARGET_PERCENT,
            "input_number.zoe_charge_target",
            DEFAULT_ZOE_CHARGE_TARGET_PERCENT,
        )
        range_target = self._option_or_helper(
            CONF_ZOE_CHARGE_RANGE_TARGET_KM,
            "input_number.zoe_charge_range_target",
            DEFAULT_ZOE_CHARGE_RANGE_TARGET_KM,
        )
        max_energy_price = self._option_or_helper(
            CONF_ZOE_MAX_ENERGY_PRICE,
            "input_number.zoe_max_energy_price",
            DEFAULT_ZOE_MAX_ENERGY_PRICE,
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
                        CONF_ZOE_SMART_CHARGING_ENABLED,
                        default=smart_charging_enabled,
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_ZOE_MAX_PRICE_ENABLED,
                        default=max_price_enabled,
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_ZOE_MAX_ENERGY_PRICE,
                        default=max_energy_price,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=-20,
                            max=100,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="c/kWh",
                        )
                    ),
                    vol.Required(
                        CONF_ZOE_CHARGE_TARGET_MODE,
                        default=target_mode,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=["SOC (%)", "Range (km)"],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_ZOE_CHARGE_TARGET_PERCENT,
                        default=target_percent,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=50,
                            max=100,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="%",
                        )
                    ),
                    vol.Required(
                        CONF_ZOE_CHARGE_RANGE_TARGET_KM,
                        default=range_target,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=10,
                            max=400,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="km",
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
            return self._create_merged_entry(
                user_input,
                clear_missing=(
                    key for key, _default, _domain in IMMAX_OPTIONAL_ENTITY_FIELDS
                ),
            )

        schema = {
            vol.Required(
                key,
                default=self.config_entry.options.get(key, default),
            ): EntitySelector(EntitySelectorConfig(domain=domain))
            for key, default, domain in IMMAX_REQUIRED_ENTITY_FIELDS
        }
        for key, default, domain in IMMAX_OPTIONAL_ENTITY_FIELDS:
            selected = self.config_entry.options.get(key, default)
            marker = (
                vol.Optional(key, description={"suggested_value": selected})
                if selected
                else vol.Optional(key)
            )
            schema[marker] = EntitySelector(EntitySelectorConfig(domain=domain))

        return self.async_show_form(
            step_id="immax_entities",
            data_schema=vol.Schema(schema),
        )

    async def async_step_cost_model(self, user_input=None):
        """Configure energy-price and battery-model setpoints."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="cost_model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DELIVERY_PRICE_EXCL_VAT,
                        default=options.get(
                            CONF_DELIVERY_PRICE_EXCL_VAT,
                            DEFAULT_DELIVERY_PRICE_EXCL_VAT,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=1,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="EUR/kWh",
                        )
                    ),
                    vol.Required(
                        CONF_ENERGY_VAT_PERCENT,
                        default=options.get(
                            CONF_ENERGY_VAT_PERCENT,
                            DEFAULT_ENERGY_VAT_PERCENT,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="%",
                        )
                    ),
                    vol.Required(
                        CONF_BATTERY_CAPACITY_KWH,
                        default=options.get(
                            CONF_BATTERY_CAPACITY_KWH,
                            DEFAULT_BATTERY_CAPACITY_KWH,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=20,
                            max=100,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="kWh",
                        )
                    ),
                    vol.Required(
                        CONF_CHARGING_EFFICIENCY_PERCENT,
                        default=options.get(
                            CONF_CHARGING_EFFICIENCY_PERCENT,
                            DEFAULT_CHARGING_EFFICIENCY_PERCENT,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=50,
                            max=100,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="%",
                        )
                    ),
                    vol.Required(
                        CONF_DEFAULT_CHARGING_POWER_KW,
                        default=options.get(
                            CONF_DEFAULT_CHARGING_POWER_KW,
                            DEFAULT_DEFAULT_CHARGING_POWER_KW,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=22,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="kW",
                        )
                    ),
                    vol.Required(
                        CONF_FALLBACK_CONSUMPTION_KWH_100,
                        default=options.get(
                            CONF_FALLBACK_CONSUMPTION_KWH_100,
                            DEFAULT_FALLBACK_CONSUMPTION_KWH_100,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=5,
                            max=50,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="kWh/100 km",
                        )
                    ),
                }
            ),
        )

    async def async_step_immax_setpoints(self, user_input=None):
        """Configure the IMMAX controller setpoints."""
        helper_defaults = {
            CONF_IMMAX_SMART_CHARGING_MODE: self._option_or_helper(
                CONF_IMMAX_SMART_CHARGING_MODE,
                "input_select.immax_smart_charging_mode",
                DEFAULT_IMMAX_SMART_CHARGING_MODE,
            ),
            CONF_IMMAX_SOLAR_PHASE_MODE: self._option_or_helper(
                CONF_IMMAX_SOLAR_PHASE_MODE,
                "input_select.immax_solar_phase_mode",
                DEFAULT_IMMAX_SOLAR_PHASE_MODE,
            ),
            CONF_IMMAX_MAX_PRICE_ENABLED: self._option_or_helper(
                CONF_IMMAX_MAX_PRICE_ENABLED,
                "input_boolean.immax_max_price_enabled",
                DEFAULT_IMMAX_MAX_PRICE_ENABLED,
            ),
            CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED: self._option_or_helper(
                CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED,
                "input_boolean.immax_charge_to_percentage_enabled",
                DEFAULT_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED,
            ),
            CONF_IMMAX_AI_ADVISOR_ENABLED: self._option_or_helper(
                CONF_IMMAX_AI_ADVISOR_ENABLED,
                "input_boolean.immax_ai_advisor_enabled",
                DEFAULT_IMMAX_AI_ADVISOR_ENABLED,
            ),
            CONF_IMMAX_DELAY_PERIOD: self._option_or_helper(
                CONF_IMMAX_DELAY_PERIOD,
                "input_number.immax_delay_period",
                DEFAULT_IMMAX_DELAY_PERIOD,
            ),
            CONF_IMMAX_TOTAL_POWER_LIMIT: self._option_or_helper(
                CONF_IMMAX_TOTAL_POWER_LIMIT,
                "input_number.immax_total_power_limit",
                DEFAULT_IMMAX_TOTAL_POWER_LIMIT,
            ),
            CONF_IMMAX_BATTERY_SOC_STOP_LIMIT: self._option_or_helper(
                CONF_IMMAX_BATTERY_SOC_STOP_LIMIT,
                "input_number.immax_battery_soc_stop_limit",
                DEFAULT_IMMAX_BATTERY_SOC_STOP_LIMIT,
            ),
            CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT: self._option_or_helper(
                CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT,
                "input_number.immax_battery_soc_resume_limit",
                DEFAULT_IMMAX_BATTERY_SOC_RESUME_LIMIT,
            ),
            CONF_IMMAX_AI_ADVISOR_INTERVAL: self._option_or_helper(
                CONF_IMMAX_AI_ADVISOR_INTERVAL,
                "input_number.immax_ai_advisor_interval",
                DEFAULT_IMMAX_AI_ADVISOR_INTERVAL,
            ),
            CONF_IMMAX_AI_CURRENT_CAP: self._option_or_helper(
                CONF_IMMAX_AI_CURRENT_CAP,
                "input_number.immax_ai_current_cap",
                DEFAULT_IMMAX_AI_CURRENT_CAP,
            ),
            CONF_IMMAX_MAX_ENERGY_PRICE: self._option_or_helper(
                CONF_IMMAX_MAX_ENERGY_PRICE,
                "input_number.immax_max_energy_price",
                DEFAULT_IMMAX_MAX_ENERGY_PRICE,
            ),
            CONF_IMMAX_ENERGY_TO_ADD: self._option_or_helper(
                CONF_IMMAX_ENERGY_TO_ADD,
                "input_number.immax_energy_to_add",
                DEFAULT_IMMAX_ENERGY_TO_ADD,
            ),
            CONF_IMMAX_CHARGE_TARGET_PERCENTAGE: self._option_or_helper(
                CONF_IMMAX_CHARGE_TARGET_PERCENTAGE,
                "input_number.immax_charge_target_percentage",
                DEFAULT_IMMAX_CHARGE_TARGET_PERCENTAGE,
            ),
            CONF_IMMAX_NORDPOOL_CURRENT: self._option_or_helper(
                CONF_IMMAX_NORDPOOL_CURRENT,
                "input_number.immax_nordpool_current",
                DEFAULT_IMMAX_NORDPOOL_CURRENT,
            ),
            CONF_IMMAX_PLANNING_POWER: self._option_or_helper(
                CONF_IMMAX_PLANNING_POWER,
                "input_number.immax_planning_power",
                DEFAULT_IMMAX_PLANNING_POWER,
            ),
            CONF_IMMAX_SOLAR_RESERVE_POWER: self._option_or_helper(
                CONF_IMMAX_SOLAR_RESERVE_POWER,
                "input_number.immax_solar_reserve_power",
                DEFAULT_IMMAX_SOLAR_RESERVE_POWER,
            ),
            CONF_IMMAX_SOLAR_MIN_POWER: self._option_or_helper(
                CONF_IMMAX_SOLAR_MIN_POWER,
                "input_number.immax_solar_min_power",
                DEFAULT_IMMAX_SOLAR_MIN_POWER,
            ),
            CONF_IMMAX_SOLAR_MAX_POWER: self._option_or_helper(
                CONF_IMMAX_SOLAR_MAX_POWER,
                "input_number.immax_solar_max_power",
                DEFAULT_IMMAX_SOLAR_MAX_POWER,
            ),
        }
        values = user_input or helper_defaults
        errors = {}
        if user_input is not None:
            if (
                user_input[CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT]
                <= user_input[CONF_IMMAX_BATTERY_SOC_STOP_LIMIT]
            ):
                errors["base"] = "soc_resume_must_exceed_stop"
            elif (
                user_input[CONF_IMMAX_SOLAR_MAX_POWER]
                < user_input[CONF_IMMAX_SOLAR_MIN_POWER]
            ):
                errors["base"] = "solar_max_must_reach_min"
            else:
                return self._create_merged_entry(user_input)

        def number_field(
            key,
            minimum,
            maximum,
            step,
            unit,
        ):
            return {
                vol.Required(key, default=values[key]): NumberSelector(
                    NumberSelectorConfig(
                        min=minimum,
                        max=maximum,
                        step=step,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement=unit,
                    )
                )
            }

        schema = {
            vol.Required(
                CONF_IMMAX_SMART_CHARGING_MODE,
                default=values[CONF_IMMAX_SMART_CHARGING_MODE],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["Off", "Nord Pool", "Solar surplus"],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_IMMAX_SOLAR_PHASE_MODE,
                default=values[CONF_IMMAX_SOLAR_PHASE_MODE],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["Auto", "1 phase", "3 phases"],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_IMMAX_MAX_PRICE_ENABLED,
                default=values[CONF_IMMAX_MAX_PRICE_ENABLED],
            ): BooleanSelector(),
            vol.Required(
                CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED,
                default=values[CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED],
            ): BooleanSelector(),
            vol.Required(
                CONF_IMMAX_AI_ADVISOR_ENABLED,
                default=values[CONF_IMMAX_AI_ADVISOR_ENABLED],
            ): BooleanSelector(),
        }
        for field in (
            number_field(CONF_IMMAX_DELAY_PERIOD, 1, 12, 1, "h"),
            number_field(CONF_IMMAX_TOTAL_POWER_LIMIT, 1.4, 30, 0.1, "kW"),
            number_field(CONF_IMMAX_BATTERY_SOC_STOP_LIMIT, 0, 99, 1, "%"),
            number_field(CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT, 1, 100, 1, "%"),
            number_field(CONF_IMMAX_AI_ADVISOR_INTERVAL, 5, 120, 5, "s"),
            number_field(CONF_IMMAX_AI_CURRENT_CAP, 6, 32, 1, "A"),
            number_field(CONF_IMMAX_MAX_ENERGY_PRICE, -20, 100, 0.1, "c/kWh"),
            number_field(CONF_IMMAX_ENERGY_TO_ADD, 1, 80, 0.5, "kWh"),
            number_field(CONF_IMMAX_CHARGE_TARGET_PERCENTAGE, 1, 100, 1, "%"),
            number_field(CONF_IMMAX_NORDPOOL_CURRENT, 6, 32, 1, "A"),
            number_field(CONF_IMMAX_PLANNING_POWER, 1, 22, 0.1, "kW"),
            number_field(CONF_IMMAX_SOLAR_RESERVE_POWER, -22, 5, 0.1, "kW"),
            number_field(CONF_IMMAX_SOLAR_MIN_POWER, 1.4, 22, 0.1, "kW"),
            number_field(CONF_IMMAX_SOLAR_MAX_POWER, 1.4, 22, 0.1, "kW"),
        ):
            schema.update(field)

        return self.async_show_form(
            step_id="immax_setpoints",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
