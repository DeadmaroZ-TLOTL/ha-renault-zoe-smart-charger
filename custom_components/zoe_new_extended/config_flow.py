"""Config flow for Zoe New Extended."""

import asyncio
import json
import logging

from uuid import uuid4

from aiohttp import ClientError, ClientSession, ClientTimeout, CookieJar
import voluptuous as vol

from renault_api.const import AVAILABLE_LOCALES
from renault_api.gigya.exceptions import GigyaException

from homeassistant import config_entries
from homeassistant.components.renault.const import RenaultConfigurationKeys
from homeassistant.components.renault.renault_hub import RenaultHub
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    ACCOUNT_TYPE_ELEKTRUM_DRIVE,
    ACCOUNT_TYPE_MOBILLY,
    CONF_ACCOUNT_ACTION,
    CONF_ACCOUNT_ENABLED,
    CONF_ACCOUNT_ID,
    CONF_ACCOUNT_NAME,
    CONF_ACCOUNT_TYPE,
    CONF_ALLOW_ANY_LOCATION,
    CONF_ALLOWED_ZONES,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_CHARGING_EFFICIENCY_PERCENT,
    CONF_CHARGING_ACCOUNTS,
    CONF_DASHBOARD_LANGUAGE,
    CONF_DEFAULT_CHARGING_POWER_KW,
    CONF_DELIVERY_PRICE_EXCL_VAT,
    CONF_ELEKTRUM_DRIVE_ENABLED,
    CONF_ELEKTRUM_ACCESS_TOKEN,
    CONF_ELEKTRUM_AGREEMENT_ID,
    CONF_ELEKTRUM_AGREEMENT_NUMBER,
    CONF_ELEKTRUM_COUNTRY_CODE,
    CONF_ELEKTRUM_DEVICE_UUID,
    CONF_ELEKTRUM_PHONE,
    CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
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
    CONF_IMMAX_FEATURE_ENABLED,
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
    CONF_MOBILLY_ACCESS_TOKEN,
    CONF_MOBILLY_PASSWORD,
    CONF_MOBILLY_PHONE,
    CONF_MOBILLY_REFRESH_TOKEN,
    CONF_MOBILLY_USERNAME,
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
    DEFAULT_IMMAX_FEATURE_ENABLED,
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
    DEFAULT_ELEKTRUM_DRIVE_ENABLED,
    DEFAULT_ELEKTRUM_COUNTRY_CODE,
    DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
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
from .elektrum_auth import (
    authentication_complete_personal_code,
    authenticated_personal_code,
    extract_authentication_token,
    personal_code_candidates,
    personal_code_format,
    verification_code,
)
from .elektrum_login import (
    elektrum_login_token,
    elektrum_mobile_headers,
    elektrum_sms_form,
    elektrum_verify_form,
    normalize_elektrum_phone,
)
from .charging_accounts_data import elektrum_token_can_replace
from .mobilly_auth import (
    MOBILLY_AUTH_URL,
    mobilly_access_token,
    mobilly_app_headers,
    mobilly_refresh_token,
    mobilly_token_credentials,
    normalize_mobilly_phone,
)

_LOGGER = logging.getLogger(__name__)

ELEKTRUM_API_URL = "https://eup.elektrum.lv/api/v3"
ELEKTRUM_AUTHENTICATION_URL = (
    "https://eup.elektrum.lv/lv/authentication?countryCode=lv"
)
ELEKTRUM_AUTHENTICATION_COMPLETE_URL = (
    "https://eup.elektrum.lv/lv/authentication/complete"
)
ELEKTRUM_IDENTITY_URL = "https://id.elektrum.lv/api/v1/authentication"
ELEKTRUM_HEADERS = elektrum_mobile_headers()
ELEKTRUM_WEB_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/json",
    "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36"
    ),
}
ELEKTRUM_REQUEST_TIMEOUT = ClientTimeout(total=20)
ELEKTRUM_AGREEMENT_PROFILE_TYPE = 3
ELEKTRUM_PERSONAL_CODE = "personal_code"
ELEKTRUM_AGREEMENT_SELECTION = "agreement_selection"
ELEKTRUM_SMART_ID_CONFIRM = "confirm"
ELEKTRUM_SMART_ID_CODE = "verification_code"
ELEKTRUM_SMART_ID_POLL_ATTEMPTS = 6
ELEKTRUM_SMART_ID_POLL_INTERVAL = 2
ELEKTRUM_CAPTCHA_SOLUTION = "captcha_solution"
ELEKTRUM_SMS_CODE = "sms_code"
RENAULT_ENTRY_SELECTION = "renault_entry_selection"
RENAULT_LOCALE = "renault_locale"
RENAULT_USERNAME = "renault_username"
RENAULT_PASSWORD = "renault_password"
RENAULT_KAMEREON_ACCOUNT_ID = "renault_kamereon_account_id"
MOBILLY_OTP_CODE = "otp_code"


def _normalize_elektrum_personal_code(value):
    """Match the digits-only value submitted by the Elektrum Android app."""
    return "".join(
        character
        for character in str(value or "")
        if character.isascii() and character.isdigit()
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
                "charging_accounts",
                "renault_account",
                "immax_setpoints",
                "immax_entities",
            ],
        )

    async def async_step_dashboard(self, user_input=None):
        """Configure dashboard language and optional modules."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        language = self.config_entry.options.get(
            CONF_DASHBOARD_LANGUAGE,
            DEFAULT_DASHBOARD_LANGUAGE,
        )
        immax_enabled = self.config_entry.options.get(
            CONF_IMMAX_FEATURE_ENABLED,
            DEFAULT_IMMAX_FEATURE_ENABLED,
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
                    vol.Required(
                        CONF_IMMAX_FEATURE_ENABLED,
                        default=immax_enabled,
                    ): BooleanSelector(),
                }
            ),
        )

    async def async_step_renault_account(self, user_input=None):
        """Select the official Renault account to sign in again."""
        entries = self.hass.config_entries.async_entries("renault")
        if not entries:
            return self.async_abort(reason="renault_account_not_found")

        if len(entries) == 1:
            entry_id = entries[0].entry_id
        elif user_input is not None:
            entry_id = str(user_input[RENAULT_ENTRY_SELECTION])
        else:
            options = [
                {
                    "value": entry.entry_id,
                    "label": str(
                        entry.data.get("username")
                        or entry.title
                        or entry.entry_id
                    ),
                }
                for entry in entries
            ]
            return self.async_show_form(
                step_id="renault_account",
                data_schema=vol.Schema(
                    {
                        vol.Required(RENAULT_ENTRY_SELECTION): SelectSelector(
                            SelectSelectorConfig(
                                options=options,
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        )
                    }
                ),
            )

        if not any(entry.entry_id == entry_id for entry in entries):
            return self.async_abort(reason="renault_account_not_found")
        self._renault_entry_id = entry_id
        return await self.async_step_renault_credentials()

    def _renault_entry(self):
        """Return the Renault config entry selected by this options flow."""
        entry_id = getattr(self, "_renault_entry_id", None)
        return next(
            (
                entry
                for entry in self.hass.config_entries.async_entries("renault")
                if entry.entry_id == entry_id
            ),
            None,
        )

    async def async_step_renault_credentials(self, user_input=None):
        """Authenticate through the same client as the core Renault flow."""
        entry = self._renault_entry()
        if entry is None:
            return self.async_abort(reason="renault_account_not_found")

        errors = {}
        if user_input is not None:
            locale = str(user_input[RENAULT_LOCALE])
            username = str(user_input[RENAULT_USERNAME]).strip()
            password = str(user_input[RENAULT_PASSWORD])
            hub = RenaultHub(self.hass, locale)
            try:
                login_success = await hub.attempt_login(username, password)
            except (ClientError, GigyaException):
                errors["base"] = "renault_connection_failed"
            except Exception:  # pragma: no cover - defensive cloud boundary
                _LOGGER.exception("Unexpected Renault login error")
                errors["base"] = "unknown"
            else:
                if login_success and hub.login_token:
                    account_ids = await hub.get_account_ids()
                    if not account_ids:
                        errors["base"] = "renault_no_account"
                    else:
                        self._renault_login_hub = hub
                        self._renault_login_data = {
                            RenaultConfigurationKeys.LOCALE: locale,
                            RenaultConfigurationKeys.USERNAME: username,
                            RenaultConfigurationKeys.PASSWORD: password,
                            RenaultConfigurationKeys.LOGIN_TOKEN: hub.login_token,
                            **AVAILABLE_LOCALES[locale],
                        }
                        current_account_id = entry.data.get(
                            RenaultConfigurationKeys.KAMEREON_ACCOUNT_ID
                        )
                        if current_account_id in account_ids:
                            return await self._async_finish_renault_login(
                                current_account_id
                            )
                        if len(account_ids) == 1:
                            return await self._async_finish_renault_login(
                                account_ids[0]
                            )
                        self._renault_account_ids = list(account_ids)
                        return await self.async_step_renault_kamereon()
                else:
                    errors["base"] = "renault_invalid_credentials"

        locale = str(
            entry.data.get(RenaultConfigurationKeys.LOCALE) or "en_GB"
        )
        if locale not in AVAILABLE_LOCALES:
            locale = next(iter(AVAILABLE_LOCALES))
        username = str(
            entry.data.get(RenaultConfigurationKeys.USERNAME) or ""
        )
        return self.async_show_form(
            step_id="renault_credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(RENAULT_LOCALE, default=locale): SelectSelector(
                        SelectSelectorConfig(
                            options=list(AVAILABLE_LOCALES),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        RENAULT_USERNAME, default=username
                    ): TextSelector(),
                    vol.Required(RENAULT_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_renault_kamereon(self, user_input=None):
        """Choose an account when Renault returns more than one."""
        account_ids = list(getattr(self, "_renault_account_ids", []))
        if not account_ids:
            return self.async_abort(reason="renault_account_not_found")
        if user_input is not None:
            account_id = str(user_input[RENAULT_KAMEREON_ACCOUNT_ID])
            if account_id not in account_ids:
                return self.async_abort(reason="renault_account_not_found")
            return await self._async_finish_renault_login(account_id)
        return self.async_show_form(
            step_id="renault_kamereon",
            data_schema=vol.Schema(
                {
                    vol.Required(RENAULT_KAMEREON_ACCOUNT_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=account_ids,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def _async_finish_renault_login(self, account_id):
        """Update and reload the selected official Renault config entry."""
        entry = self._renault_entry()
        data = getattr(self, "_renault_login_data", None)
        if entry is None or not isinstance(data, dict):
            return self.async_abort(reason="renault_account_not_found")
        updated_data = {
            **entry.data,
            **data,
            RenaultConfigurationKeys.KAMEREON_ACCOUNT_ID: account_id,
        }
        self.hass.config_entries.async_update_entry(entry, data=updated_data)
        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_create_entry(
            title="",
            data=dict(self.config_entry.options),
        )

    @property
    def _charging_accounts(self):
        """Return copies of configured account records."""
        raw_accounts = self.config_entry.data.get(CONF_CHARGING_ACCOUNTS, [])
        if not isinstance(raw_accounts, list):
            return []
        return [dict(account) for account in raw_accounts if isinstance(account, dict)]

    def _save_charging_accounts(self, accounts):
        """Store secrets in config-entry data, outside ordinary options."""
        self._update_charging_accounts(accounts)
        return self.async_create_entry(
            title="",
            data=dict(self.config_entry.options),
        )

    def _update_charging_accounts(self, accounts):
        """Update charging-account secrets while keeping the options flow open."""
        data = dict(self.config_entry.data)
        data[CONF_CHARGING_ACCOUNTS] = accounts
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)

    def _selected_account(self):
        selected_id = getattr(self, "_selected_account_id", None)
        return next(
            (
                account
                for account in self._charging_accounts
                if account.get(CONF_ACCOUNT_ID) == selected_id
            ),
            None,
        )

    async def async_step_charging_accounts(self, user_input=None):
        """Add, edit, or remove any number of charging accounts."""
        accounts = self._charging_accounts
        is_lv = str(self.hass.config.language).lower().startswith("lv")
        actions = [
            {
                "value": "add:mobilly",
                "label": (
                    "Pievienot Mobilly kontu" if is_lv else "Add Mobilly account"
                ),
            },
            {
                "value": "add:elektrum_drive",
                "label": (
                    "Pievienot Elektrum Drive kontu"
                    if is_lv
                    else "Add Elektrum Drive account"
                ),
            },
        ]
        for account in accounts:
            account_id = account.get(CONF_ACCOUNT_ID)
            name = account.get(CONF_ACCOUNT_NAME) or account.get(CONF_ACCOUNT_TYPE)
            account_type = account.get(CONF_ACCOUNT_TYPE)
            enabled = account.get(CONF_ACCOUNT_ENABLED, True)
            state = (
                ("ieslēgts" if enabled else "izslēgts")
                if is_lv
                else ("enabled" if enabled else "disabled")
            )
            actions.extend(
                (
                    {
                        "value": f"edit:{account_id}",
                        "label": (
                            f"Rediģēt {name} ({account_type}, {state})"
                            if is_lv
                            else f"Edit {name} ({account_type}, {state})"
                        ),
                    },
                    {
                        "value": f"remove:{account_id}",
                        "label": (
                            f"Noņemt {name}" if is_lv else f"Remove {name}"
                        ),
                    },
                )
            )
            if account_type == ACCOUNT_TYPE_ELEKTRUM_DRIVE:
                actions.append(
                    {
                        "value": f"link:{account_id}",
                        "label": (
                            f"Piesaistīt Elektrum Drive līgumu kontam {name}"
                            if is_lv
                            else f"Link Elektrum Drive agreement for {name}"
                        ),
                    }
                )
                actions.append(
                    {
                        "value": f"login:{account_id}",
                        "label": (
                            f"Pieslēgt Elektrum Drive lietotni kontam {name}"
                            if is_lv
                            else f"Log in to Elektrum Drive app for {name}"
                        ),
                    }
                )
            if account_type == ACCOUNT_TYPE_MOBILLY:
                actions.append(
                    {
                        "value": f"mobile:{account_id}",
                        "label": (
                            f"Piesaistīt Mobilly lietotni kontam {name}"
                            if is_lv
                            else f"Link Mobilly app for {name}"
                        ),
                    }
                )

        if user_input is not None:
            action, _, account_id = user_input[CONF_ACCOUNT_ACTION].partition(":")
            if action == "add":
                self._selected_account_id = None
                if account_id == ACCOUNT_TYPE_MOBILLY:
                    return await self.async_step_mobilly_account()
                return await self.async_step_elektrum_account()
            self._selected_account_id = account_id
            if action == "remove":
                return await self.async_step_remove_charging_account()
            if action == "link":
                return await self.async_step_elektrum_link_agreement()
            if action == "login":
                return await self.async_step_elektrum_mobile_login()
            if action == "mobile":
                return await self.async_step_mobilly_mobile()
            selected = self._selected_account()
            if selected and selected.get(CONF_ACCOUNT_TYPE) == ACCOUNT_TYPE_MOBILLY:
                return await self.async_step_mobilly_account()
            return await self.async_step_elektrum_account()

        return self.async_show_form(
            step_id="charging_accounts",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT_ACTION): SelectSelector(
                        SelectSelectorConfig(
                            options=actions,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            description_placeholders={"account_count": str(len(accounts))},
        )

    async def async_step_mobilly_account(self, user_input=None):
        """Add or edit one Mobilly account."""
        account = self._selected_account()
        errors = {}
        if user_input is not None:
            username = str(user_input.get(CONF_MOBILLY_USERNAME) or "").strip()
            password = str(user_input.get(CONF_MOBILLY_PASSWORD) or "")
            if not password and account is not None:
                password = str(account.get(CONF_MOBILLY_PASSWORD) or "")
            phone = normalize_mobilly_phone(
                user_input.get(CONF_MOBILLY_PHONE)
                or (account or {}).get(CONF_MOBILLY_PHONE)
            )
            if phone and len(phone) < 10:
                errors["base"] = "mobilly_phone_invalid"
            elif bool(username) != bool(password):
                errors["base"] = "mobilly_credentials_required"
            elif not (username and password) and not phone:
                errors["base"] = "mobilly_credentials_required"
            else:
                updated = {
                    CONF_ACCOUNT_ID: (
                        account.get(CONF_ACCOUNT_ID) if account else uuid4().hex
                    ),
                    CONF_ACCOUNT_TYPE: ACCOUNT_TYPE_MOBILLY,
                    CONF_ACCOUNT_NAME: str(
                        user_input.get(CONF_ACCOUNT_NAME) or "Mobilly"
                    ).strip(),
                    CONF_ACCOUNT_ENABLED: bool(
                        user_input.get(CONF_ACCOUNT_ENABLED, True)
                    ),
                    CONF_MOBILLY_USERNAME: username,
                    CONF_MOBILLY_PASSWORD: password,
                }
                if phone:
                    updated[CONF_MOBILLY_PHONE] = phone
                if (
                    account is not None
                    and phone == account.get(CONF_MOBILLY_PHONE)
                ):
                    for key in (
                        CONF_MOBILLY_ACCESS_TOKEN,
                        CONF_MOBILLY_REFRESH_TOKEN,
                    ):
                        if account.get(key):
                            updated[key] = account[key]
                accounts = self._charging_accounts
                if account is None:
                    accounts.append(updated)
                else:
                    accounts = [
                        updated
                        if item.get(CONF_ACCOUNT_ID) == account.get(CONF_ACCOUNT_ID)
                        else item
                        for item in accounts
                    ]
                if phone and not updated.get(CONF_MOBILLY_ACCESS_TOKEN):
                    self._update_charging_accounts(accounts)
                    self._selected_account_id = updated[CONF_ACCOUNT_ID]
                    return await self.async_step_mobilly_mobile(
                        {CONF_MOBILLY_PHONE: phone}
                    )
                return self._save_charging_accounts(accounts)

        return self.async_show_form(
            step_id="mobilly_account",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ACCOUNT_NAME,
                        default=(account or {}).get(CONF_ACCOUNT_NAME, "Mobilly"),
                    ): TextSelector(TextSelectorConfig()),
                    vol.Required(
                        CONF_ACCOUNT_ENABLED,
                        default=(account or {}).get(CONF_ACCOUNT_ENABLED, True),
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_MOBILLY_USERNAME,
                        default=(account or {}).get(CONF_MOBILLY_USERNAME, ""),
                    ): TextSelector(TextSelectorConfig()),
                    vol.Optional(CONF_MOBILLY_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Optional(
                        CONF_MOBILLY_PHONE,
                        default=(account or {}).get(CONF_MOBILLY_PHONE, ""),
                    ): TextSelector(TextSelectorConfig()),
                }
            ),
            errors=errors,
            description_placeholders={
                "mode": "edit" if account else "add",
            },
        )

    async def async_step_mobilly_mobile(self, user_input=None):
        """Start Mobilly's app SMS authentication for live station data."""
        account = self._selected_account()
        if account is None or account.get(CONF_ACCOUNT_TYPE) != ACCOUNT_TYPE_MOBILLY:
            return await self.async_step_charging_accounts()

        errors = {}
        default_phone = normalize_mobilly_phone(
            account.get(CONF_MOBILLY_PHONE)
            or account.get(CONF_MOBILLY_USERNAME)
        )
        if user_input is not None:
            phone = normalize_mobilly_phone(user_input.get(CONF_MOBILLY_PHONE))
            if len(phone) < 10:
                errors["base"] = "mobilly_phone_invalid"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    async with session.post(
                        f"{MOBILLY_AUTH_URL}/otp-session/start",
                        headers=mobilly_app_headers(),
                        json={"phoneNumber": phone},
                        timeout=ELEKTRUM_REQUEST_TIMEOUT,
                    ) as response:
                        await response.read()
                        status = response.status
                except (ClientError, TimeoutError):
                    errors["base"] = "mobilly_mobile_connection_failed"
                else:
                    if status >= 400:
                        _LOGGER.warning(
                            "Mobilly OTP start failed with HTTP %s", status
                        )
                        errors["base"] = "mobilly_otp_start_failed"
                    else:
                        self._mobilly_pending_phone = phone
                        return await self.async_step_mobilly_otp()

        return self.async_show_form(
            step_id="mobilly_mobile",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MOBILLY_PHONE,
                        default=default_phone,
                    ): TextSelector(TextSelectorConfig())
                }
            ),
            errors=errors,
            description_placeholders={
                "account_name": str(account.get(CONF_ACCOUNT_NAME) or "Mobilly")
            },
        )

    async def async_step_mobilly_otp(self, user_input=None):
        """Exchange the Mobilly SMS code for a refreshable app session."""
        account = self._selected_account()
        phone = normalize_mobilly_phone(
            getattr(self, "_mobilly_pending_phone", "")
        )
        if account is None or not phone:
            return await self.async_step_mobilly_mobile()

        errors = {}
        if user_input is not None:
            otp = "".join(
                character
                for character in str(user_input.get(MOBILLY_OTP_CODE) or "")
                if character.isdigit()
            )
            if not otp:
                errors["base"] = "mobilly_otp_required"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    async with session.post(
                        f"{MOBILLY_AUTH_URL}/token/otp",
                        headers=mobilly_app_headers(),
                        json=mobilly_token_credentials(
                            phone,
                            otp,
                            grant_type="otp",
                        )["tokenCredentials"],
                        timeout=ELEKTRUM_REQUEST_TIMEOUT,
                    ) as response:
                        payload = await self._async_elektrum_response_payload(
                            response
                        )
                        status = response.status
                except (ClientError, TimeoutError):
                    errors["base"] = "mobilly_mobile_connection_failed"
                else:
                    access_token = mobilly_access_token(payload)
                    refresh_token = mobilly_refresh_token(payload)
                    if status >= 400 or not access_token:
                        _LOGGER.warning(
                            "Mobilly OTP exchange failed with HTTP %s", status
                        )
                        errors["base"] = "mobilly_otp_failed"
                    else:
                        updated = dict(account)
                        updated[CONF_MOBILLY_PHONE] = phone
                        updated[CONF_MOBILLY_ACCESS_TOKEN] = access_token
                        if refresh_token:
                            updated[CONF_MOBILLY_REFRESH_TOKEN] = refresh_token
                        accounts = [
                            updated
                            if item.get(CONF_ACCOUNT_ID)
                            == account.get(CONF_ACCOUNT_ID)
                            else item
                            for item in self._charging_accounts
                        ]
                        self._mobilly_pending_phone = ""
                        return self._save_charging_accounts(accounts)

        return self.async_show_form(
            step_id="mobilly_otp",
            data_schema=vol.Schema(
                {
                    vol.Required(MOBILLY_OTP_CODE): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
            description_placeholders={"phone_suffix": phone[-4:]},
        )

    async def async_step_elektrum_mobile_login(self, user_input=None):
        """Send the official Elektrum Drive app SMS verification code."""
        account = self._selected_account()
        if (
            account is None
            or account.get(CONF_ACCOUNT_TYPE) != ACCOUNT_TYPE_ELEKTRUM_DRIVE
        ):
            return await self.async_step_charging_accounts()

        errors = {}
        country_code = str(
            (account or {}).get(CONF_ELEKTRUM_COUNTRY_CODE)
            or DEFAULT_ELEKTRUM_COUNTRY_CODE
        ).lstrip("+")
        default_phone = normalize_elektrum_phone(
            account.get(CONF_ELEKTRUM_PHONE), country_code
        )
        if user_input is not None:
            country_code = "".join(
                character
                for character in str(
                    user_input.get(CONF_ELEKTRUM_COUNTRY_CODE) or country_code
                )
                if character.isdigit()
            )
            phone = normalize_elektrum_phone(
                user_input.get(CONF_ELEKTRUM_PHONE), country_code
            )
            captcha_solution = str(
                user_input.get(ELEKTRUM_CAPTCHA_SOLUTION) or ""
            ).strip()
            device_uuid = str(
                account.get(CONF_ELEKTRUM_DEVICE_UUID) or uuid4()
            )
            if len(phone) < 8 or not country_code:
                errors["base"] = "elektrum_phone_invalid"
            elif len(captcha_solution) < 20 or captcha_solution.startswith("."):
                errors["base"] = "elektrum_captcha_required"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    async with session.post(
                        f"{ELEKTRUM_API_URL}/auth/sms",
                        headers={
                            **ELEKTRUM_HEADERS,
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data=elektrum_sms_form(
                            phone,
                            country_code,
                            device_uuid,
                            captcha_solution,
                        ),
                        timeout=ELEKTRUM_REQUEST_TIMEOUT,
                    ) as response:
                        payload = await self._async_elektrum_response_payload(
                            response
                        )
                        status = response.status
                except (ClientError, TimeoutError):
                    errors["base"] = "elektrum_connection_failed"
                else:
                    if status >= 400:
                        _LOGGER.warning(
                            "Elektrum Drive SMS login failed with HTTP %s "
                            "(API error %s)",
                            status,
                            self._elektrum_error_code(payload),
                        )
                        errors["base"] = "elektrum_sms_start_failed"
                    else:
                        self._elektrum_login_phone = phone
                        self._elektrum_login_country_code = country_code
                        self._elektrum_login_device_uuid = device_uuid
                        return await self.async_step_elektrum_mobile_verify()

        return self.async_show_form(
            step_id="elektrum_mobile_login",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ELEKTRUM_PHONE,
                        default=default_phone,
                    ): TextSelector(TextSelectorConfig()),
                    vol.Required(
                        CONF_ELEKTRUM_COUNTRY_CODE,
                        default=country_code,
                    ): TextSelector(TextSelectorConfig()),
                    vol.Required(ELEKTRUM_CAPTCHA_SOLUTION): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "account_name": str(account.get(CONF_ACCOUNT_NAME) or ""),
                "captcha_url": "https://eup.elektrum.lv/lv/captcha",
            },
        )

    async def async_step_elektrum_mobile_verify(self, user_input=None):
        """Exchange the Elektrum Drive SMS code for an app session."""
        account = self._selected_account()
        phone = str(getattr(self, "_elektrum_login_phone", "") or "")
        country_code = str(
            getattr(self, "_elektrum_login_country_code", "") or ""
        )
        device_uuid = str(
            getattr(self, "_elektrum_login_device_uuid", "") or ""
        )
        if account is None or not phone or not country_code or not device_uuid:
            return await self.async_step_elektrum_mobile_login()

        errors = {}
        if user_input is not None:
            sms_code = "".join(
                character
                for character in str(user_input.get(ELEKTRUM_SMS_CODE) or "")
                if character.isdigit()
            )
            if not sms_code:
                errors["base"] = "elektrum_sms_code_required"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    async with session.post(
                        f"{ELEKTRUM_API_URL}/auth/verify",
                        headers={
                            **ELEKTRUM_HEADERS,
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data=elektrum_verify_form(
                            phone,
                            sms_code,
                            country_code,
                            device_uuid,
                        ),
                        timeout=ELEKTRUM_REQUEST_TIMEOUT,
                    ) as response:
                        payload = await self._async_elektrum_response_payload(
                            response
                        )
                        status = response.status
                    access_token = elektrum_login_token(payload)
                    profile_payload = {}
                    profile_status = 599
                    if status < 400 and access_token:
                        profile_payload, profile_status = (
                            await self._async_elektrum_api_raw(
                                "GET", "user", access_token
                            )
                        )
                except (ClientError, TimeoutError):
                    errors["base"] = "elektrum_connection_failed"
                else:
                    if status >= 400 or not access_token:
                        _LOGGER.warning(
                            "Elektrum Drive SMS verification failed with "
                            "HTTP %s (API error %s)",
                            status,
                            self._elektrum_error_code(payload),
                        )
                        errors["base"] = "elektrum_sms_verify_failed"
                    elif profile_status >= 400:
                        errors["base"] = "elektrum_connection_failed"
                    else:
                        current_payload = None
                        previous_token = str(
                            account.get(CONF_ELEKTRUM_ACCESS_TOKEN) or ""
                        )
                        if previous_token:
                            try:
                                current_payload, current_status = (
                                    await self._async_elektrum_api_raw(
                                        "GET", "user", previous_token
                                    )
                                )
                                if current_status >= 400:
                                    current_payload = None
                            except (ClientError, TimeoutError):
                                current_payload = None
                        if not elektrum_token_can_replace(
                            current_payload,
                            profile_payload,
                            saved_agreement=bool(
                                account.get(CONF_ELEKTRUM_AGREEMENT_ID)
                            ),
                        ):
                            errors["base"] = "elektrum_linked_session_required"
                        else:
                            updated = dict(account)
                            updated[CONF_ELEKTRUM_PHONE] = phone
                            updated[CONF_ELEKTRUM_COUNTRY_CODE] = country_code
                            updated[CONF_ELEKTRUM_DEVICE_UUID] = device_uuid
                            updated[CONF_ELEKTRUM_ACCESS_TOKEN] = access_token
                            agreements = self._elektrum_agreements(profile_payload)
                            selected = next(
                                (
                                    item
                                    for item in agreements
                                    if item.get("selected")
                                ),
                                agreements[0] if len(agreements) == 1 else None,
                            )
                            if selected is not None:
                                updated[CONF_ELEKTRUM_AGREEMENT_ID] = str(
                                    selected["id"]
                                )
                                updated[CONF_ELEKTRUM_AGREEMENT_NUMBER] = str(
                                    selected.get("number") or ""
                                )
                            accounts = [
                                updated
                                if item.get(CONF_ACCOUNT_ID)
                                == account.get(CONF_ACCOUNT_ID)
                                else item
                                for item in self._charging_accounts
                            ]
                            self._elektrum_login_phone = ""
                            self._elektrum_login_country_code = ""
                            self._elektrum_login_device_uuid = ""
                            return self._save_charging_accounts(accounts)

        return self.async_show_form(
            step_id="elektrum_mobile_verify",
            data_schema=vol.Schema(
                {
                    vol.Required(ELEKTRUM_SMS_CODE): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
            description_placeholders={"phone_suffix": phone[-4:]},
        )

    async def async_step_elektrum_account(self, user_input=None):
        """Add or edit one Elektrum Drive account and its app token."""
        account = self._selected_account()
        errors = {}
        if user_input is not None:
            submitted_token = str(
                user_input.get(CONF_ELEKTRUM_ACCESS_TOKEN) or ""
            ).strip()
            access_token = submitted_token
            if not access_token and account is not None:
                access_token = str(
                    account.get(CONF_ELEKTRUM_ACCESS_TOKEN) or ""
                )
            device_uuid = str(
                user_input.get(CONF_ELEKTRUM_DEVICE_UUID) or ""
            ).strip()
            if not device_uuid and account is not None:
                device_uuid = str(
                    account.get(CONF_ELEKTRUM_DEVICE_UUID) or ""
                )
            if not device_uuid:
                device_uuid = str(uuid4())
            previous_token = str(
                (account or {}).get(CONF_ELEKTRUM_ACCESS_TOKEN) or ""
            )
            token_changed = bool(submitted_token) and submitted_token != previous_token
            if token_changed:
                try:
                    candidate_payload, candidate_status = (
                        await self._async_elektrum_api_raw(
                            "GET", "user", submitted_token
                        )
                    )
                    current_payload = None
                    if previous_token:
                        current_payload, current_status = (
                            await self._async_elektrum_api_raw(
                                "GET", "user", previous_token
                            )
                        )
                        if current_status >= 400:
                            current_payload = None
                except (ClientError, TimeoutError):
                    errors["base"] = "elektrum_connection_failed"
                else:
                    if candidate_status == 401:
                        errors["base"] = "elektrum_session_expired"
                    elif candidate_status >= 400:
                        errors["base"] = "elektrum_connection_failed"
                    elif not elektrum_token_can_replace(
                        current_payload,
                        candidate_payload,
                        saved_agreement=bool(
                            (account or {}).get(CONF_ELEKTRUM_AGREEMENT_ID)
                        ),
                    ):
                        errors["base"] = "elektrum_linked_session_required"

            if not errors:
                updated = {
                    CONF_ACCOUNT_ID: (
                        account.get(CONF_ACCOUNT_ID) if account else uuid4().hex
                    ),
                    CONF_ACCOUNT_TYPE: ACCOUNT_TYPE_ELEKTRUM_DRIVE,
                    CONF_ACCOUNT_NAME: str(
                        user_input.get(CONF_ACCOUNT_NAME) or "Elektrum Drive"
                    ).strip(),
                    CONF_ACCOUNT_ENABLED: bool(
                        user_input.get(CONF_ACCOUNT_ENABLED, True)
                    ),
                    CONF_ELEKTRUM_PHONE: str(
                        user_input.get(CONF_ELEKTRUM_PHONE) or ""
                    ).strip(),
                    CONF_ELEKTRUM_COUNTRY_CODE: str(
                        user_input.get(CONF_ELEKTRUM_COUNTRY_CODE)
                        or DEFAULT_ELEKTRUM_COUNTRY_CODE
                    ).lstrip("+"),
                    CONF_ELEKTRUM_ACCESS_TOKEN: access_token,
                    CONF_ELEKTRUM_DEVICE_UUID: device_uuid,
                }
                if account is not None:
                    for key in (
                        CONF_ELEKTRUM_AGREEMENT_ID,
                        CONF_ELEKTRUM_AGREEMENT_NUMBER,
                    ):
                        if account.get(key):
                            updated[key] = account[key]
                accounts = self._charging_accounts
                if account is None:
                    accounts.append(updated)
                else:
                    accounts = [
                        updated
                        if item.get(CONF_ACCOUNT_ID)
                        == account.get(CONF_ACCOUNT_ID)
                        else item
                        for item in accounts
                    ]
                return self._save_charging_accounts(accounts)

        return self.async_show_form(
            step_id="elektrum_account",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ACCOUNT_NAME,
                        default=(account or {}).get(
                            CONF_ACCOUNT_NAME, "Elektrum Drive"
                        ),
                    ): TextSelector(TextSelectorConfig()),
                    vol.Required(
                        CONF_ACCOUNT_ENABLED,
                        default=(account or {}).get(CONF_ACCOUNT_ENABLED, True),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_ELEKTRUM_PHONE,
                        default=(account or {}).get(CONF_ELEKTRUM_PHONE, ""),
                    ): TextSelector(TextSelectorConfig()),
                    vol.Required(
                        CONF_ELEKTRUM_COUNTRY_CODE,
                        default=(account or {}).get(
                            CONF_ELEKTRUM_COUNTRY_CODE,
                            DEFAULT_ELEKTRUM_COUNTRY_CODE,
                        ),
                    ): TextSelector(TextSelectorConfig()),
                    vol.Optional(CONF_ELEKTRUM_ACCESS_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Optional(CONF_ELEKTRUM_DEVICE_UUID): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            description_placeholders={
                "mode": "edit" if account else "add",
            },
            errors=errors,
        )

    async def async_step_remove_charging_account(self, user_input=None):
        """Confirm removal of one charging account."""
        account = self._selected_account()
        if account is None:
            return await self.async_step_charging_accounts()
        errors = {}
        if user_input is not None:
            if user_input.get("confirm"):
                accounts = [
                    item
                    for item in self._charging_accounts
                    if item.get(CONF_ACCOUNT_ID) != account.get(CONF_ACCOUNT_ID)
                ]
                return self._save_charging_accounts(accounts)
            errors["base"] = "account_removal_not_confirmed"
        return self.async_show_form(
            step_id="remove_charging_account",
            data_schema=vol.Schema(
                {vol.Required("confirm", default=False): BooleanSelector()}
            ),
            errors=errors,
            description_placeholders={
                "account_name": str(account.get(CONF_ACCOUNT_NAME) or ""),
            },
        )

    async def async_step_elektrum_link_agreement(self, user_input=None):
        """Start Elektrum's required Smart-ID agreement authorization."""
        account = self._selected_account()
        if (
            account is None
            or account.get(CONF_ACCOUNT_TYPE) != ACCOUNT_TYPE_ELEKTRUM_DRIVE
        ):
            return await self.async_step_charging_accounts()

        pending_error = getattr(self, "_elektrum_link_error", None)
        self._elektrum_link_error = None
        errors = {"base": pending_error} if pending_error else {}
        if user_input is not None:
            personal_code = _normalize_elektrum_personal_code(
                user_input.get(ELEKTRUM_PERSONAL_CODE)
            )
            if not personal_code:
                errors["base"] = "elektrum_personal_code_required"
            elif len(personal_code) != 11:
                errors["base"] = "elektrum_personal_code_invalid"
            else:
                try:
                    payload, status, identity_token = (
                        await self._async_start_elektrum_smart_id(personal_code)
                    )
                except (ClientError, TimeoutError):
                    errors["base"] = "elektrum_connection_failed"
                else:
                    code = verification_code(payload)
                    if status >= 400:
                        _LOGGER.warning(
                            "Elektrum Smart-ID authorization failed with "
                            "HTTP %s (API error %s)",
                            status,
                            self._elektrum_error_code(payload),
                        )
                        errors["base"] = "elektrum_smart_id_start_failed"
                    elif not identity_token or not code:
                        errors["base"] = "elektrum_smart_id_start_failed"
                    else:
                        self._elektrum_identity_token = identity_token
                        self._elektrum_pending_personal_code = personal_code
                        self._elektrum_verification_code = code
                        return await self.async_step_elektrum_smart_id()

        return self.async_show_form(
            step_id="elektrum_link_agreement",
            data_schema=vol.Schema(
                {
                    vol.Required(ELEKTRUM_PERSONAL_CODE): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "account_name": str(account.get(CONF_ACCOUNT_NAME) or "")
            },
        )

    async def async_step_elektrum_smart_id(self, user_input=None):
        """Wait for Smart-ID, then authorize and discover postpaid agreements."""
        account = self._selected_account()
        identity_token = str(
            getattr(self, "_elektrum_identity_token", "") or ""
        )
        code = str(getattr(self, "_elektrum_verification_code", "") or "")
        if account is None or not identity_token or not code:
            return await self.async_step_elektrum_link_agreement()

        errors = {}
        if user_input is not None:
            if not user_input.get(ELEKTRUM_SMART_ID_CONFIRM):
                errors["base"] = "elektrum_smart_id_not_confirmed"
            else:
                try:
                    payload, status = await self._async_poll_elektrum_smart_id(
                        identity_token
                    )
                except (ClientError, TimeoutError):
                    errors["base"] = "elektrum_connection_failed"
                else:
                    if status == 202:
                        errors["base"] = "elektrum_smart_id_pending"
                    elif status >= 400:
                        _LOGGER.warning(
                            "Elektrum Smart-ID poll failed with HTTP %s "
                            "(API error %s)",
                            status,
                            self._elektrum_error_code(payload),
                        )
                        errors["base"] = "elektrum_smart_id_failed"
                    else:
                        personal_code = authenticated_personal_code(payload)
                        try:
                            completed_code, complete_status = (
                                await self._async_complete_elektrum_smart_id()
                            )
                        except (ClientError, TimeoutError):
                            completed_code = ""
                            complete_status = 599
                        if not completed_code:
                            _LOGGER.warning(
                                "Elektrum Smart-ID completion did not return "
                                "the verified callback (HTTP %s); using the "
                                "successfully authenticated Smart-ID request",
                                complete_status,
                            )

                        personal_code = (
                            completed_code
                            or personal_code
                            or getattr(
                                self,
                                "_elektrum_pending_personal_code",
                                "",
                            )
                            or ""
                        )
                        _LOGGER.debug(
                            "Elektrum Smart-ID returned a verified callback (%s)",
                            personal_code_format(personal_code),
                        )
                        await self._async_clear_elektrum_smart_id()
                        if not personal_code_candidates(personal_code):
                            self._elektrum_link_error = (
                                "elektrum_smart_id_failed"
                            )
                            return await self.async_step_elektrum_link_agreement()

                        agreements, error = (
                            await self._async_discover_elektrum_agreements(
                                account,
                                personal_code,
                            )
                        )
                        if error:
                            self._elektrum_link_error = error
                            return await self.async_step_elektrum_link_agreement()

                        self._elektrum_pending_agreements = agreements
                        if len(agreements) == 1:
                            return await self._async_select_elektrum_agreement(
                                agreements[0]
                            )
                        return await self.async_step_elektrum_select_agreement()

        return self.async_show_form(
            step_id="elektrum_smart_id",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ELEKTRUM_SMART_ID_CODE,
                        default=code,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[code],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        ELEKTRUM_SMART_ID_CONFIRM,
                        default=True,
                    ): BooleanSelector()
                }
            ),
            errors=errors,
            description_placeholders={"verification_code": code},
        )

    async def _async_clear_elektrum_smart_id(self):
        """Discard all short-lived identity data held by this options flow."""
        self._elektrum_identity_token = ""
        self._elektrum_pending_personal_code = ""
        self._elektrum_verification_code = ""
        self._elektrum_auth_cookie_header = ""
        session = getattr(self, "_elektrum_auth_session", None)
        self._elektrum_auth_session = None
        if session is not None and not session.closed:
            await session.close()

    async def _async_discover_elektrum_agreements(
        self,
        account,
        personal_code,
    ):
        """Use an identity-confirmed code to discover Elektrum agreements."""
        payload = {}
        status = 400
        try:
            candidates = personal_code_candidates(personal_code)
            for candidate_index, candidate in enumerate(candidates):
                payload, status = await self._async_elektrum_api_request(
                    account,
                    "PUT",
                    "user/authorize",
                    json_body={"personalCode": candidate},
                )
                if status < 400 or status == 401:
                    break
                _LOGGER.warning(
                    "Elektrum agreement authorization rejected candidate %s/%s "
                    "(%s) "
                    "personal-code format with HTTP %s (API error %s)",
                    candidate_index + 1,
                    len(candidates),
                    personal_code_format(candidate),
                    status,
                    self._elektrum_error_code(payload),
                )
        except (ClientError, TimeoutError):
            return [], "elektrum_connection_failed"

        if status == 401:
            return [], "elektrum_session_expired"
        if status >= 400:
            _LOGGER.warning(
                "Elektrum agreement authorization failed with HTTP %s "
                "(API error %s)",
                status,
                self._elektrum_error_code(payload),
            )
            return [], "elektrum_authorization_failed"

        agreements = self._elektrum_agreements(payload)
        user_status = 0
        if not agreements:
            try:
                user_payload, user_status = await self._async_elektrum_api_request(
                    account,
                    "GET",
                    "user",
                )
            except (ClientError, TimeoutError):
                user_status = 599
                user_payload = {}
            if user_status < 400:
                agreements = self._elektrum_agreements(user_payload)

        if agreements:
            return agreements, None
        return (
            [],
            "elektrum_connection_failed"
            if user_status >= 500
            else "elektrum_no_agreements",
        )

    async def async_step_elektrum_select_agreement(self, user_input=None):
        """Select one agreement when authorization returns several."""
        agreements = getattr(self, "_elektrum_pending_agreements", [])
        if not agreements:
            return await self.async_step_elektrum_link_agreement()

        pending_error = getattr(self, "_elektrum_agreement_error", None)
        self._elektrum_agreement_error = None
        errors = {"base": pending_error} if pending_error else {}
        if user_input is not None:
            agreement_id = str(
                user_input.get(ELEKTRUM_AGREEMENT_SELECTION) or ""
            )
            agreement = next(
                (
                    item
                    for item in agreements
                    if str(item.get("id") or "") == agreement_id
                ),
                None,
            )
            if agreement is None:
                errors["base"] = "elektrum_agreement_required"
            else:
                return await self._async_select_elektrum_agreement(agreement)

        options = [
            {
                "value": str(agreement["id"]),
                "label": self._elektrum_agreement_label(agreement),
            }
            for agreement in agreements
        ]
        return self.async_show_form(
            step_id="elektrum_select_agreement",
            data_schema=vol.Schema(
                {
                    vol.Required(ELEKTRUM_AGREEMENT_SELECTION): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def _async_select_elektrum_agreement(self, agreement):
        """Set the Elektrum profile to the selected postpaid agreement."""
        account = self._selected_account()
        if account is None:
            return await self.async_step_charging_accounts()
        try:
            payload, status = await self._async_elektrum_api_request(
                account,
                "PATCH",
                "user",
                json_body={
                    "type": ELEKTRUM_AGREEMENT_PROFILE_TYPE,
                    "agreementId": str(agreement["id"]),
                },
            )
        except ClientError:
            self._elektrum_agreement_error = "elektrum_connection_failed"
            return await self.async_step_elektrum_select_agreement()

        profile = payload.get("data") if isinstance(payload, dict) else None
        profile_type = profile.get("type") if isinstance(profile, dict) else None
        verify_status = 0
        if status < 400 and profile_type != ELEKTRUM_AGREEMENT_PROFILE_TYPE:
            try:
                verify_payload, verify_status = await self._async_elektrum_api_request(
                    account,
                    "GET",
                    "user",
                )
            except ClientError:
                verify_status = 599
                verify_payload = {}
            verified = (
                verify_payload.get("data")
                if isinstance(verify_payload, dict)
                else None
            )
            profile_type = (
                verified.get("type") if isinstance(verified, dict) else None
            )

        if status >= 400 or profile_type != ELEKTRUM_AGREEMENT_PROFILE_TYPE:
            self._elektrum_agreement_error = (
                "elektrum_connection_failed"
                if status < 400 and verify_status >= 500
                else "elektrum_agreement_link_failed"
            )
            return await self.async_step_elektrum_select_agreement()

        updated = dict(account)
        updated[CONF_ELEKTRUM_AGREEMENT_ID] = str(agreement["id"])
        updated[CONF_ELEKTRUM_AGREEMENT_NUMBER] = str(
            agreement.get("number") or ""
        )
        accounts = [
            updated
            if item.get(CONF_ACCOUNT_ID) == account.get(CONF_ACCOUNT_ID)
            else item
            for item in self._charging_accounts
        ]
        return self._save_charging_accounts(accounts)

    async def _async_start_elektrum_smart_id(self, personal_code):
        """Start the same Smart-ID flow used by the Elektrum Android app."""
        previous_session = getattr(self, "_elektrum_auth_session", None)
        if previous_session is not None and not previous_session.closed:
            await previous_session.close()
        session = ClientSession(
            cookie_jar=CookieJar(quote_cookie=False),
            headers=ELEKTRUM_WEB_HEADERS,
            timeout=ELEKTRUM_REQUEST_TIMEOUT,
        )
        self._elektrum_auth_session = session
        try:
            async with session.get(ELEKTRUM_AUTHENTICATION_URL) as response:
                page = await response.text()
                page_status = response.status
        except Exception:
            await session.close()
            self._elektrum_auth_session = None
            raise
        if page_status >= 400:
            await session.close()
            self._elektrum_auth_session = None
            return {"error": {"code": f"auth_page_http_{page_status}"}}, page_status, ""

        identity_token = extract_authentication_token(page)
        if not identity_token:
            await session.close()
            self._elektrum_auth_session = None
            return {"error": {"code": "missing_identity_token"}}, 502, ""
        cookie_names = {cookie.key for cookie in session.cookie_jar}
        if "elektrum_car_charging_session" not in cookie_names:
            await session.close()
            self._elektrum_auth_session = None
            return {"error": {"code": "missing_auth_cookies"}}, 502, ""

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {identity_token}",
            "Content-Type": "application/json",
            "Origin": "https://eup.elektrum.lv",
            "Referer": ELEKTRUM_AUTHENTICATION_URL,
        }
        async with session.post(
            f"{ELEKTRUM_IDENTITY_URL}/smart-id/authenticate",
            headers=headers,
            json={"nationalIdentityNumber": personal_code},
        ) as response:
            payload = await self._async_elektrum_response_payload(response)
            status = response.status
        if status >= 400:
            await session.close()
            self._elektrum_auth_session = None
        return payload, status, identity_token

    async def _async_poll_elektrum_smart_id(self, identity_token):
        """Poll briefly for a user-approved Smart-ID authentication."""
        session = getattr(self, "_elektrum_auth_session", None)
        if session is None or session.closed:
            return {"error": {"code": "missing_auth_session"}}, 503
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {identity_token}",
            "Content-Type": "application/json",
            "Origin": "https://eup.elektrum.lv",
            "Referer": ELEKTRUM_AUTHENTICATION_URL,
        }
        payload = {}
        status = 202
        for attempt in range(ELEKTRUM_SMART_ID_POLL_ATTEMPTS):
            async with session.get(
                f"{ELEKTRUM_IDENTITY_URL}/smart-id/poll",
                headers=headers,
            ) as response:
                payload = await self._async_elektrum_response_payload(response)
                status = response.status
            if status != 202:
                break
            if attempt + 1 < ELEKTRUM_SMART_ID_POLL_ATTEMPTS:
                await asyncio.sleep(ELEKTRUM_SMART_ID_POLL_INTERVAL)
        return payload, status

    async def _async_complete_elektrum_smart_id(self):
        """Complete the browser callback and return Elektrum's verified code."""
        session = getattr(self, "_elektrum_auth_session", None)
        if session is None or session.closed:
            return "", 502

        headers = {
            "Referer": ELEKTRUM_AUTHENTICATION_URL,
        }
        async with session.get(
            ELEKTRUM_AUTHENTICATION_COMPLETE_URL,
            headers=headers,
        ) as response:
            page = await response.text()
            status = response.status
        return authentication_complete_personal_code(page), status

    @staticmethod
    async def _async_elektrum_response_payload(response):
        """Parse JSON while retaining a non-sensitive identifier for errors."""
        body = await response.text()
        try:
            payload = json.loads(body) if body else {}
        except (TypeError, ValueError):
            payload = {
                "_response": {
                    "status": response.status,
                    "content_type": str(response.content_type or "unknown"),
                }
            }
        return payload if isinstance(payload, dict) else {}

    async def _async_elektrum_api_request(
        self,
        account,
        method,
        path,
        *,
        json_body=None,
    ):
        """Call the Elektrum app API and refresh an expired token once."""
        token = str(account.get(CONF_ELEKTRUM_ACCESS_TOKEN) or "")
        payload, status = await self._async_elektrum_api_raw(
            method,
            path,
            token,
            json_body=json_body,
        )
        if status != 401:
            return payload, status

        refresh_payload, refresh_status = await self._async_elektrum_api_raw(
            "GET",
            "auth/refresh",
            token,
        )
        refreshed_token = self._elektrum_access_token(refresh_payload)
        if refresh_status >= 400 or not refreshed_token:
            return payload, status

        if account.get(CONF_ELEKTRUM_AGREEMENT_ID):
            profile_payload, profile_status = await self._async_elektrum_api_raw(
                "GET",
                "user",
                refreshed_token,
            )
            if profile_status >= 400 or not elektrum_token_can_replace(
                None,
                profile_payload,
                saved_agreement=True,
            ):
                _LOGGER.warning(
                    "Refusing to replace an Elektrum linked session with an "
                    "anonymous refreshed profile"
                )
                return payload, status

        account[CONF_ELEKTRUM_ACCESS_TOKEN] = refreshed_token
        self._replace_charging_account(account)
        return await self._async_elektrum_api_raw(
            method,
            path,
            refreshed_token,
            json_body=json_body,
        )

    async def _async_elektrum_api_raw(
        self,
        method,
        path,
        token,
        *,
        json_body=None,
    ):
        session = async_get_clientsession(self.hass)
        headers = {
            **ELEKTRUM_HEADERS,
            "Authorization": f"Bearer {token}",
        }
        async with session.request(
            method,
            f"{ELEKTRUM_API_URL}/{path}",
            headers=headers,
            json=json_body,
            timeout=ELEKTRUM_REQUEST_TIMEOUT,
        ) as response:
            payload = await self._async_elektrum_response_payload(response)
        return payload if isinstance(payload, dict) else {}, response.status

    def _replace_charging_account(self, updated):
        accounts = [
            updated
            if item.get(CONF_ACCOUNT_ID) == updated.get(CONF_ACCOUNT_ID)
            else item
            for item in self._charging_accounts
        ]
        data = dict(self.config_entry.data)
        data[CONF_CHARGING_ACCOUNTS] = accounts
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)

    @staticmethod
    def _elektrum_agreements(payload):
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict) and isinstance(data.get("user"), dict):
            data = data["user"]
        raw = data.get("agreements") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            return []
        return [
            dict(item)
            for item in raw
            if isinstance(item, dict) and item.get("id")
        ]

    @staticmethod
    def _elektrum_agreement_label(agreement):
        number = str(agreement.get("number") or "Agreement")
        agreement_type = str(agreement.get("type") or "").strip()
        return f"{number} ({agreement_type})" if agreement_type else number

    @staticmethod
    def _elektrum_access_token(payload):
        if not isinstance(payload, dict):
            return ""
        data = payload.get("data")
        if isinstance(data, dict):
            return str(
                data.get("accessToken")
                or data.get("access_token")
                or data.get("token")
                or ""
            )
        return str(payload.get("accessToken") or payload.get("token") or "")

    @staticmethod
    def _elektrum_error_code(payload):
        """Return a non-sensitive Elektrum API error identifier for logs."""
        if not isinstance(payload, dict):
            return "unknown"
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("code") or error.get("id") or "unknown")
        response = payload.get("_response")
        if isinstance(response, dict):
            status = response.get("status") or "unknown"
            content_type = response.get("content_type") or "unknown"
            return f"http_{status}:{content_type}"
        return str(payload.get("code") or "unknown")

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
                        CONF_ELEKTRUM_DRIVE_ENABLED,
                        default=options.get(
                            CONF_ELEKTRUM_DRIVE_ENABLED,
                            DEFAULT_ELEKTRUM_DRIVE_ENABLED,
                        ),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
                        default=options.get(
                            CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
                            DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT,
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
            CONF_IMMAX_FEATURE_ENABLED: self._option_or_helper(
                CONF_IMMAX_FEATURE_ENABLED,
                "input_boolean.immax_feature_enabled",
                DEFAULT_IMMAX_FEATURE_ENABLED,
            ),
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
                CONF_IMMAX_FEATURE_ENABLED,
                default=values[CONF_IMMAX_FEATURE_ENABLED],
            ): BooleanSelector(),
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
