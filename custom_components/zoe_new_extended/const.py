"""Constants for Zoe New Extended."""

DOMAIN = "zoe_new_extended"
CONF_CHARGING_ACCOUNTS = "charging_accounts"
CONF_ACCOUNT_ACTION = "account_action"
CONF_ACCOUNT_ENABLED = "enabled"
CONF_ACCOUNT_ID = "id"
CONF_ACCOUNT_NAME = "name"
CONF_ACCOUNT_TYPE = "type"
CONF_MOBILLY_USERNAME = "username"
CONF_MOBILLY_PASSWORD = "password"
CONF_MOBILLY_PHONE = "mobile_phone"
CONF_MOBILLY_ACCESS_TOKEN = "mobile_access_token"
CONF_MOBILLY_REFRESH_TOKEN = "mobile_refresh_token"
CONF_ELEKTRUM_PHONE = "phone"
CONF_ELEKTRUM_COUNTRY_CODE = "country_code"
CONF_ELEKTRUM_ACCESS_TOKEN = "access_token"
CONF_ELEKTRUM_DEVICE_UUID = "device_uuid"
CONF_ELEKTRUM_AGREEMENT_ID = "agreement_id"
CONF_ELEKTRUM_AGREEMENT_NUMBER = "agreement_number"
CONF_AMPECO_EMAIL = "email"
CONF_AMPECO_ACCESS_TOKEN = "ampeco_access_token"
CONF_AMPECO_REFRESH_TOKEN = "ampeco_refresh_token"
CONF_AMPECO_TOKEN_EXPIRES_AT = "ampeco_token_expires_at"
CONF_AMPECO_LOGIN_LINK = "login_link"
CONF_AMPECO_GOOGLE_ACCESS_TOKEN = "google_access_token"
ACCOUNT_TYPE_MOBILLY = "mobilly"
ACCOUNT_TYPE_ELEKTRUM_DRIVE = "elektrum_drive"
ACCOUNT_TYPE_IGNITIS_ON = "ignitis_on"
ACCOUNT_TYPE_IKRAUTAS = "ikrautas"
DEFAULT_ELEKTRUM_COUNTRY_CODE = "371"
CONF_DASHBOARD_LANGUAGE = "dashboard_language"
CONF_ALLOWED_ZONES = "allowed_zones"
CONF_ALLOW_ANY_LOCATION = "allow_any_location"
CONF_LOCATION_CONTROL_ENABLED = "location_control_enabled"
CONF_NORDPOOL_AREA = "nordpool_area"
CONF_ZOE_CHARGE_RANGE_TARGET_KM = "zoe_charge_range_target_km"
CONF_ZOE_CHARGE_TARGET_MODE = "zoe_charge_target_mode"
CONF_ZOE_CHARGE_TARGET_PERCENT = "zoe_charge_target_percent"
CONF_ZOE_MAX_ENERGY_PRICE = "zoe_max_energy_price"
CONF_ZOE_MAX_PRICE_ENABLED = "zoe_max_price_enabled"
CONF_ZOE_SMART_CHARGING_ENABLED = "zoe_smart_charging_enabled"
CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
CONF_CHARGING_EFFICIENCY_PERCENT = "charging_efficiency_percent"
CONF_DEFAULT_CHARGING_POWER_KW = "default_charging_power_kw"
CONF_DELIVERY_PRICE_EXCL_VAT = "delivery_price_excl_vat"
CONF_ENERGY_VAT_PERCENT = "energy_vat_percent"
CONF_FALLBACK_CONSUMPTION_KWH_100 = "fallback_consumption_kwh_100"
CONF_ELEKTRUM_DRIVE_ENABLED = "elektrum_drive_enabled"
CONF_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT = (
    "elektrum_postpaid_discount_percent"
)
CONF_IMMAX_BATTERY_CHARGE_ENTITY = "immax_battery_charge_entity"
CONF_IMMAX_BATTERY_DISCHARGE_ENTITY = "immax_battery_discharge_entity"
CONF_IMMAX_CHARGER_CURRENT_ENTITY = "immax_charger_current_entity"
CONF_IMMAX_CHARGER_ENERGY_ENTITY = "immax_charger_energy_entity"
CONF_IMMAX_CHARGER_ONLINE_ENTITY = "immax_charger_online_entity"
CONF_IMMAX_CHARGER_PROBLEM_ENTITY = "immax_charger_problem_entity"
CONF_IMMAX_CHARGER_STATUS_ENTITY = "immax_charger_status_entity"
CONF_IMMAX_CHARGER_SWITCH_ENTITY = "immax_charger_switch_entity"
CONF_IMMAX_CURRENT_A_ENTITY = "immax_current_a_entity"
CONF_IMMAX_CURRENT_B_ENTITY = "immax_current_b_entity"
CONF_IMMAX_CURRENT_C_ENTITY = "immax_current_c_entity"
CONF_IMMAX_FEATURE_ENABLED = "immax_feature_enabled"
CONF_IMMAX_GRID_EXPORT_ENTITY = "immax_grid_export_entity"
CONF_IMMAX_NORDPOOL_PRICE_ENTITY = "immax_nordpool_price_entity"
CONF_IMMAX_POWER_A_ENTITY = "immax_power_a_entity"
CONF_IMMAX_POWER_B_ENTITY = "immax_power_b_entity"
CONF_IMMAX_POWER_C_ENTITY = "immax_power_c_entity"
CONF_IMMAX_SOLAR_POWER_ENTITY = "immax_solar_power_entity"
CONF_IMMAX_TOTAL_LOAD_ENTITY = "immax_total_load_entity"
CONF_IMMAX_VEHICLE_SOC_ENTITY = "immax_vehicle_soc_entity"
CONF_IMMAX_VOLTAGE_A_ENTITY = "immax_voltage_a_entity"
CONF_IMMAX_VOLTAGE_B_ENTITY = "immax_voltage_b_entity"
CONF_IMMAX_VOLTAGE_C_ENTITY = "immax_voltage_c_entity"
CONF_IMMAX_AI_ADVISOR_ENABLED = "immax_ai_advisor_enabled"
CONF_IMMAX_AI_ADVISOR_INTERVAL = "immax_ai_advisor_interval"
CONF_IMMAX_AI_CURRENT_CAP = "immax_ai_current_cap"
CONF_IMMAX_BATTERY_SOC_RESUME_LIMIT = "immax_battery_soc_resume_limit"
CONF_IMMAX_BATTERY_SOC_STOP_LIMIT = "immax_battery_soc_stop_limit"
CONF_IMMAX_CHARGE_TARGET_PERCENTAGE = "immax_charge_target_percentage"
CONF_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED = "immax_charge_to_percentage_enabled"
CONF_IMMAX_DELAY_PERIOD = "immax_delay_period"
CONF_IMMAX_ENERGY_TO_ADD = "immax_energy_to_add"
CONF_IMMAX_MAX_ENERGY_PRICE = "immax_max_energy_price"
CONF_IMMAX_MAX_PRICE_ENABLED = "immax_max_price_enabled"
CONF_IMMAX_NORDPOOL_CURRENT = "immax_nordpool_current"
CONF_IMMAX_PLANNING_POWER = "immax_planning_power"
CONF_IMMAX_SMART_CHARGING_MODE = "immax_smart_charging_mode"
CONF_IMMAX_SOLAR_MAX_POWER = "immax_solar_max_power"
CONF_IMMAX_SOLAR_MIN_POWER = "immax_solar_min_power"
CONF_IMMAX_SOLAR_PHASE_MODE = "immax_solar_phase_mode"
CONF_IMMAX_SOLAR_RESERVE_POWER = "immax_solar_reserve_power"
CONF_IMMAX_TOTAL_POWER_LIMIT = "immax_total_power_limit"
DEFAULT_DASHBOARD_LANGUAGE = "lv"
DEFAULT_NORDPOOL_AREA = "LV"
DEFAULT_ZOE_CHARGE_RANGE_TARGET_KM = 200.0
DEFAULT_ZOE_CHARGE_TARGET_MODE = "SOC (%)"
DEFAULT_ZOE_CHARGE_TARGET_PERCENT = 100.0
DEFAULT_ZOE_MAX_ENERGY_PRICE = 5.0
DEFAULT_ZOE_MAX_PRICE_ENABLED = False
DEFAULT_ZOE_SMART_CHARGING_ENABLED = False
DEFAULT_BATTERY_CAPACITY_KWH = 52.0
DEFAULT_CHARGING_EFFICIENCY_PERCENT = 90.0
DEFAULT_DEFAULT_CHARGING_POWER_KW = 11.0
DEFAULT_DELIVERY_PRICE_EXCL_VAT = 0.03962
DEFAULT_ENERGY_VAT_PERCENT = 21.0
DEFAULT_FALLBACK_CONSUMPTION_KWH_100 = 17.5
DEFAULT_ELEKTRUM_DRIVE_ENABLED = True
DEFAULT_ELEKTRUM_POSTPAID_DISCOUNT_PERCENT = 5.0
DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY = "sensor.unibms_battery_in"
DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY = "sensor.unibms_battery_out"
DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY = "number.immax_ev_charger_current"
DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY = "sensor.immax_ev_charger_energy"
DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY = "switch.immax_ev_charger_online_state"
DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY = "binary_sensor.immax_ev_charger_problem"
DEFAULT_IMMAX_CHARGER_STATUS_ENTITY = "sensor.immax_ev_charger_status"
DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY = "switch.immax_ev_charger"
DEFAULT_IMMAX_CURRENT_A_ENTITY = "sensor.immax_ev_charger_current_a"
DEFAULT_IMMAX_CURRENT_B_ENTITY = "sensor.immax_ev_charger_current_b"
DEFAULT_IMMAX_CURRENT_C_ENTITY = "sensor.immax_ev_charger_current_c"
DEFAULT_IMMAX_FEATURE_ENABLED = True
DEFAULT_IMMAX_GRID_EXPORT_ENTITY = "sensor.solax_srd9cccxv6_feed_in_power"
DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY = "sensor.renault_zoe_new_nord_pool_price"
DEFAULT_IMMAX_POWER_A_ENTITY = "sensor.immax_ev_charger_power_a"
DEFAULT_IMMAX_POWER_B_ENTITY = "sensor.immax_ev_charger_power_b"
DEFAULT_IMMAX_POWER_C_ENTITY = "sensor.immax_ev_charger_power_c"
DEFAULT_IMMAX_SOLAR_POWER_ENTITY = "sensor.total_solar_production_2"
DEFAULT_IMMAX_TOTAL_LOAD_ENTITY = "sensor.ac_tuya_meter_power"
DEFAULT_IMMAX_VEHICLE_SOC_ENTITY = ""
DEFAULT_IMMAX_VOLTAGE_A_ENTITY = "sensor.immax_ev_charger_voltage_a"
DEFAULT_IMMAX_VOLTAGE_B_ENTITY = "sensor.immax_ev_charger_voltage_b"
DEFAULT_IMMAX_VOLTAGE_C_ENTITY = "sensor.immax_ev_charger_voltage_c"
DEFAULT_IMMAX_AI_ADVISOR_ENABLED = True
DEFAULT_IMMAX_AI_ADVISOR_INTERVAL = 15.0
DEFAULT_IMMAX_AI_CURRENT_CAP = 32.0
DEFAULT_IMMAX_BATTERY_SOC_RESUME_LIMIT = 60.0
DEFAULT_IMMAX_BATTERY_SOC_STOP_LIMIT = 50.0
DEFAULT_IMMAX_CHARGE_TARGET_PERCENTAGE = 80.0
DEFAULT_IMMAX_CHARGE_TO_PERCENTAGE_ENABLED = False
DEFAULT_IMMAX_DELAY_PERIOD = 12.0
DEFAULT_IMMAX_ENERGY_TO_ADD = 20.0
DEFAULT_IMMAX_MAX_ENERGY_PRICE = 5.0
DEFAULT_IMMAX_MAX_PRICE_ENABLED = False
DEFAULT_IMMAX_NORDPOOL_CURRENT = 32.0
DEFAULT_IMMAX_PLANNING_POWER = 12.0
DEFAULT_IMMAX_SMART_CHARGING_MODE = "Off"
DEFAULT_IMMAX_SOLAR_MAX_POWER = 22.0
DEFAULT_IMMAX_SOLAR_MIN_POWER = 1.4
DEFAULT_IMMAX_SOLAR_PHASE_MODE = "Auto"
DEFAULT_IMMAX_SOLAR_RESERVE_POWER = 0.5
DEFAULT_IMMAX_TOTAL_POWER_LIMIT = 3.5
TARGET_ENTITY_ID = "sensor.battery"
ZOE_LOCATION_ENTITY_ID = "device_tracker.location"
ZOE_ENTITY_PREFIX = "sensor.zoe_"

NORDPOOL_AREAS = {
    "AT": ("Austria", 0.20),
    "BE": ("Belgium", 0.06),
    "DK1": ("Denmark DK1", 0.25),
    "DK2": ("Denmark DK2", 0.25),
    "EE": ("Estonia", 0.24),
    "FI": ("Finland", 0.255),
    "FR": ("France", 0.055),
    "GER": ("Germany", 0.19),
    "LT": ("Lithuania", 0.21),
    "LV": ("Latvia", 0.21),
    "NL": ("Netherlands", 0.21),
    "NO1": ("Norway NO1", 0.25),
    "NO2": ("Norway NO2", 0.25),
    "NO3": ("Norway NO3", 0.25),
    "NO4": ("Norway NO4", 0.25),
    "NO5": ("Norway NO5", 0.25),
    "SE1": ("Sweden SE1", 0.25),
    "SE2": ("Sweden SE2", 0.25),
    "SE3": ("Sweden SE3", 0.25),
    "SE4": ("Sweden SE4", 0.25),
    "SYS": ("Nord Pool system", 0.25),
}

API_ENTITY_IDS = frozenset(
    {
        "sensor.zoe_charging_settings_updated",
        "sensor.zoe_last_charge_duration",
        "sensor.zoe_last_charge_end",
        "sensor.zoe_last_charge_end_battery_level",
        "sensor.zoe_last_charge_energy_recovered",
        "sensor.zoe_last_charge_start",
        "sensor.zoe_last_charge_start_battery_level",
        "sensor.zoe_last_charge_status",
    }
)
