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
    CONF_LOCATION_CONTROL_ENABLED,
    CONF_NORDPOOL_AREA,
    DEFAULT_NORDPOOL_AREA,
    DOMAIN,
    NORDPOOL_AREAS,
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
    """Configure where smart charging may operate."""

    async def async_step_init(self, user_input=None):
        """Configure allowed charging zones."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

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
            step_id="init",
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
