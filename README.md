# Renault Zoe New Extended + Smart Charger

Home Assistant companion integration for the Renault Zoe phase 2 (`X102VE`).
It extends the official Renault integration with the controls and diagnostics
used by the included Nord Pool smart charger package.

## Features

- Working start and stop charge commands for `X102VE`.
- Charging mode selector with distinct `Always`, `Delayed`, and `Scheduled` states.
- Unrecognized or missing API modes remain visible as `Unknown`.
- Renault API update and raw charge/plug diagnostics.
- Smart charging permission by one or more Home Assistant zones.
- Nord Pool country/price area selector in the integration options.
- Local Renault icon and logo on Home Assistant 2026.3 or newer.
- Optional Nord Pool planner, switchable SOC/range target, maximum spot price, deadline,
  estimated cost, and adaptive charging model.
- Optional automatic Renault Trips dashboard with day selection, route maps,
  speed samples, distance, and estimated energy consumption.

The command workaround follows the behavior proposed in
[renault-api pull request #2202](https://github.com/hacf-fr/renault-api/pull/2202).
When that fix is released and used by Home Assistant, the compatibility patch
in this integration can be removed.

## Installation

### HACS custom repository

1. Add this repository to HACS as an **Integration** custom repository.
2. Install **Renault Zoe New Extended + Smart Charger**.
3. Restart Home Assistant.
4. Add **Zoe New Extended** from **Settings > Devices & services**.

The official Renault integration must already contain a loaded Zoe phase 2.
Choose the planner's Nord Pool country under **Zoe New Extended > Configure**.
The same options dialog is the only place where smart-charging locations are
edited; the integration does not duplicate every zone as a device switch.

### Manual

Copy `custom_components/zoe_new_extended` to the same path below your Home
Assistant configuration directory, restart Home Assistant, and add the
integration from **Settings > Devices & services**.

## Smart Charger

The optional files are in [`smart_charger`](smart_charger):

- `zoe_smart_charger_package.yaml`: helpers, planner sensors, and automations.
- `lovelace_card.yaml`: compact controls and planner status card.
- `pyscript/zoe_charge_sessions.py`: optional learned charging-power and
  completed-session cost model.

Read [`smart_charger/README.md`](smart_charger/README.md) before enabling the
automation. Check every entity ID first, especially the Renault buttons and
Nord Pool price sensor.

## Renault Trips

The optional automatic trip page and the complete dashboard export are in
[`renault_trips`](renault_trips). The page calculates trips from Recorder
history and does not need manual start or stop buttons.

Read [`renault_trips/README.md`](renault_trips/README.md) for the expected
Renault entities and installation path.

## Notes

- Renault can accept a cloud command before the vehicle receives it. The
  command status sensor reports both API acceptance and later vehicle state.
- The stop workaround schedules charging 24 hours ahead because the current
  `X102VE` pause endpoint is accepted but does not stop the car in practice.
- Renault and the Renault diamond are trademarks of Renault Group. Brand
  images are the assets already maintained by Home Assistant Brands.
