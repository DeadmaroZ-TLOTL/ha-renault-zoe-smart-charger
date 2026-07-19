"""Constants for Zoe New Extended."""

DOMAIN = "zoe_new_extended"
CONF_ALLOWED_ZONES = "allowed_zones"
CONF_ALLOW_ANY_LOCATION = "allow_any_location"
CONF_LOCATION_CONTROL_ENABLED = "location_control_enabled"
TARGET_ENTITY_ID = "sensor.battery"
ZOE_LOCATION_ENTITY_ID = "device_tracker.location"
ZOE_ENTITY_PREFIX = "sensor.zoe_"

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
