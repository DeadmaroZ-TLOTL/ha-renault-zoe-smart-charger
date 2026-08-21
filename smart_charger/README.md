# Smart Charger package

This package selects the cheapest 15-minute Nord Pool slots before a chosen
deadline and controls the Renault start/stop charge buttons supplied by Home
Assistant. It also respects the locations selected in Zoe New Extended.
When smart charging is disabled or the car is outside the selected locations,
the automation changes Renault's charging mode to `Always`.
At a selected charging interval it sends Renault's normal X102VE start action
only if the vehicle has not begun charging. This resumes the car after a prior
schedule-based stop. Between selected intervals the stop button
installs a one-minute KCM schedule 24 hours ahead; this reliably stops X102VE
where Renault's accepted `pause` command has no physical effect.
The custom charging-mode select restores its last confirmed value during a
temporary Renault coordinator outage, so the dashboard control stays visible
after Home Assistant restarts.
If the remaining eligible slots cannot reach the target before the deadline,
the planner continues with the earliest later slots below the configured price
cap until the target is reached or the published price data runs out.

## Requirements

- Home Assistant `packages` enabled.
- Official Renault integration and Zoe New Extended loaded.
- Nord Pool custom integration with its `hourly` action available.
- Nord Pool country selected under **Zoe New Extended > Configure**.

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
| Nord Pool price | `sensor.renault_zoe_new_nord_pool_price` |
| Zoe SOC | `sensor.battery` |
| Plug status | `binary_sensor.plug` / `sensor.plug_state` |
| Charge status | `binary_sensor.charging` / `sensor.charge_state` |
| Start/stop | `button.start_charge` / `button.stop_charge` |
| Location guard | `binary_sensor.renault_zoe_new_smart_charging_location_allowed` |

The planner uses a 52 kWh usable battery, 90% charging efficiency, and an
11 kW fallback charge rate. Delivery is `0.03962 EUR/kWh + 21% VAT`. Adjust
these constants in the package for another vehicle or tariff.

The card can switch between an SOC target and a remaining-range target. Range
mode converts the requested kilometres to SOC using Renault's current
`sensor.battery_autonomy` estimate, so the conversion follows the car's latest
range estimate rather than a fixed kilometres-per-percent value. The SOC and
range input helpers stay synchronized when either target is changed.

## Optional adaptive model

`pyscript/zoe_charge_sessions.py` reads completed Renault charge sessions,
learns an effective charging rate, and estimates historical energy cost. It
requires the Pyscript custom integration. Change the constants at the top of
the file before installing it in `/config/pyscript`.
