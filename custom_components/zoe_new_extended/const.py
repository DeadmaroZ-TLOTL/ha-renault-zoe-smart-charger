"""Constants for Zoe New Extended."""

DOMAIN = "zoe_new_extended"
CONF_ALLOWED_ZONES = "allowed_zones"
CONF_ALLOW_ANY_LOCATION = "allow_any_location"
CONF_LOCATION_CONTROL_ENABLED = "location_control_enabled"
CONF_NORDPOOL_AREA = "nordpool_area"
CONF_IMMAX_BATTERY_CHARGE_ENTITY = "immax_battery_charge_entity"
CONF_IMMAX_BATTERY_DISCHARGE_ENTITY = "immax_battery_discharge_entity"
CONF_IMMAX_CHARGER_CURRENT_ENTITY = "immax_charger_current_entity"
CONF_IMMAX_CHARGER_ENERGY_ENTITY = "immax_charger_energy_entity"
CONF_IMMAX_CHARGER_ONLINE_ENTITY = "immax_charger_online_entity"
CONF_IMMAX_CHARGER_PROBLEM_ENTITY = "immax_charger_problem_entity"
CONF_IMMAX_CHARGER_STATUS_ENTITY = "immax_charger_status_entity"
CONF_IMMAX_CHARGER_SWITCH_ENTITY = "immax_charger_switch_entity"
CONF_IMMAX_GRID_EXPORT_ENTITY = "immax_grid_export_entity"
CONF_IMMAX_NORDPOOL_PRICE_ENTITY = "immax_nordpool_price_entity"
CONF_IMMAX_POWER_A_ENTITY = "immax_power_a_entity"
CONF_IMMAX_POWER_B_ENTITY = "immax_power_b_entity"
CONF_IMMAX_POWER_C_ENTITY = "immax_power_c_entity"
CONF_IMMAX_SOLAR_POWER_ENTITY = "immax_solar_power_entity"
CONF_IMMAX_VEHICLE_SOC_ENTITY = "immax_vehicle_soc_entity"
CONF_IMMAX_VOLTAGE_A_ENTITY = "immax_voltage_a_entity"
CONF_IMMAX_VOLTAGE_B_ENTITY = "immax_voltage_b_entity"
CONF_IMMAX_VOLTAGE_C_ENTITY = "immax_voltage_c_entity"
DEFAULT_NORDPOOL_AREA = "LV"
DEFAULT_IMMAX_BATTERY_CHARGE_ENTITY = "sensor.unibms_battery_in"
DEFAULT_IMMAX_BATTERY_DISCHARGE_ENTITY = "sensor.unibms_battery_out"
DEFAULT_IMMAX_CHARGER_CURRENT_ENTITY = "number.immax_ev_charger_current"
DEFAULT_IMMAX_CHARGER_ENERGY_ENTITY = "sensor.immax_ev_charger_energy"
DEFAULT_IMMAX_CHARGER_ONLINE_ENTITY = "switch.immax_ev_charger_online_state"
DEFAULT_IMMAX_CHARGER_PROBLEM_ENTITY = "binary_sensor.immax_ev_charger_problem"
DEFAULT_IMMAX_CHARGER_STATUS_ENTITY = "sensor.immax_ev_charger_status"
DEFAULT_IMMAX_CHARGER_SWITCH_ENTITY = "switch.immax_ev_charger"
DEFAULT_IMMAX_GRID_EXPORT_ENTITY = "sensor.solax_srd9cccxv6_feed_in_power"
DEFAULT_IMMAX_NORDPOOL_PRICE_ENTITY = "sensor.renault_zoe_new_nord_pool_price"
DEFAULT_IMMAX_POWER_A_ENTITY = "sensor.immax_ev_charger_power_a"
DEFAULT_IMMAX_POWER_B_ENTITY = "sensor.immax_ev_charger_power_b"
DEFAULT_IMMAX_POWER_C_ENTITY = "sensor.immax_ev_charger_power_c"
DEFAULT_IMMAX_SOLAR_POWER_ENTITY = "sensor.total_solar_production_2"
DEFAULT_IMMAX_VEHICLE_SOC_ENTITY = "sensor.battery"
DEFAULT_IMMAX_VOLTAGE_A_ENTITY = "sensor.immax_ev_charger_voltage_a"
DEFAULT_IMMAX_VOLTAGE_B_ENTITY = "sensor.immax_ev_charger_voltage_b"
DEFAULT_IMMAX_VOLTAGE_C_ENTITY = "sensor.immax_ev_charger_voltage_c"
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
