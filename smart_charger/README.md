# Smart Charger package

This package selects the cheapest 15-minute Nord Pool slots before a chosen
deadline and controls the Renault start/stop charge buttons supplied by Home
Assistant. It also respects the locations selected in Zoe New Extended.

## Requirements

- Home Assistant `packages` enabled.
- Official Renault integration and Zoe New Extended loaded.
- Nord Pool sensor exposing `raw_today` and `raw_tomorrow` slot attributes.
- The price sensor state and slot `value` expressed in `c/kWh`.

## Install

1. Put `zoe_smart_charger_package.yaml` in your HA packages directory.
2. Change the entity IDs marked `EDIT IF NEEDED`.
3. Include the package directory from `configuration.yaml` if it is not
   already included.
4. Run a configuration check and restart Home Assistant.
5. Add `lovelace_card.yaml` to the desired dashboard.

The default package expects these entities:

| Purpose | Entity |
| --- | --- |
| Nord Pool price | `sensor.nordpool_kwh_lv_eur_3_10_021` |
| Zoe SOC | `sensor.battery` |
| Plug status | `binary_sensor.plug` / `sensor.plug_state` |
| Charge status | `binary_sensor.charging` / `sensor.charge_state` |
| Start/stop | `button.start_charge` / `button.stop_charge` |
| Location guard | `binary_sensor.renault_zoe_new_smart_charging_location_allowed` |

The planner uses a 52 kWh usable battery, 90% charging efficiency, and an
11 kW fallback charge rate. Delivery is `0.03962 EUR/kWh + 21% VAT`. Adjust
these constants in the package for another vehicle or tariff.

## Optional adaptive model

`pyscript/zoe_charge_sessions.py` reads completed Renault charge sessions,
learns an effective charging rate, and estimates historical energy cost. It
requires the Pyscript custom integration. Change the constants at the top of
the file before installing it in `/config/pyscript`.
