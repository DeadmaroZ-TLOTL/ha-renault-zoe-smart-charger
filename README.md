# Renault Zoe New Extended + Smart Charger

Home Assistant companion integration for the Renault Zoe phase 2 (`X102VE`).
It extends the official Renault integration with the controls and diagnostics
used by the included Nord Pool smart charger package.

## Features

- Working start and stop charge commands for `X102VE`.
- Charging mode selector with `Always` and `Delayed` states.
- Missing, unknown, scheduled, and delegated modes are shown as `Delayed`.
- Renault API update and raw charge/plug diagnostics.
- Smart charging permission by one or more Home Assistant zones.
- Local Renault icon and logo on Home Assistant 2026.3 or newer.
- Optional Nord Pool planner, target SOC, maximum spot price, deadline,
  estimated cost, and adaptive charging model.

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

## Notes

- Renault can accept a cloud command before the vehicle receives it. The
  command status sensor reports both API acceptance and later vehicle state.
- The stop workaround schedules charging 24 hours ahead because the current
  `X102VE` pause endpoint is accepted but does not stop the car in practice.
- Renault and the Renault diamond are trademarks of Renault Group. Brand
  images are the assets already maintained by Home Assistant Brands.
