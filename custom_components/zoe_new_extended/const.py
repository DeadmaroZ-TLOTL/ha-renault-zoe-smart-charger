"""Constants for Zoe New Extended."""

DOMAIN = "zoe_new_extended"
CONF_ALLOWED_ZONES = "allowed_zones"
CONF_ALLOW_ANY_LOCATION = "allow_any_location"
CONF_LOCATION_CONTROL_ENABLED = "location_control_enabled"
CONF_NORDPOOL_AREA = "nordpool_area"
DEFAULT_NORDPOOL_AREA = "LV"
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
