<p align="center">
  <img src="https://raw.githubusercontent.com/DeadmaroZ-TLOTL/ha-renault-zoe-smart-charger/main/custom_components/zoe_new_extended/brand/icon.png" width="128" height="128" alt="Renault Zoe New Extended icon">
</p>

# Renault Zoe New Extended + Smart Charger

Home Assistant companion integration for the Renault Zoe phase 2 (`X102VE`).
It extends the official Renault integration with the controls and diagnostics
used by the included Nord Pool smart charger package.

## Features

- Adaptive Renault status refresh: battery and charging data refresh every five
  minutes while Zoe New is plugged in, then return to Home Assistant's normal
  Renault polling interval after unplugging.
- Working start and stop charge commands for `X102VE`.
- Charging mode selector with distinct `Always`, `Delayed`, and `Scheduled` states.
- Automatic `Always` mode when smart charging is disabled or outside an allowed location.
- Unrecognized or missing API modes remain visible as `Unknown`.
- Renault API update and raw charge/plug diagnostics.
- Current MyRenault cloud-alert count, active contracts, remote-services state,
  and battery/corrosion warranty expiry dates.
- Vehicle-specific API probing avoids creating tyre-pressure entities when the
  Renault cloud does not expose TPMS data for the VIN.
- Smart charging permission by one or more Home Assistant zones.
- Nord Pool country/price area, Renault planner targets, price cap, energy cost
  model, and IMMAX setpoints in the integration options.
- Local Renault icon and logo on Home Assistant 2026.3 or newer.
- Optional Nord Pool planner, switchable SOC/range target, maximum spot price, deadline,
  estimated cost, and adaptive charging model.
- Optional IMMAX EV charger controller with separate Nord Pool and dynamic
  solar-surplus modes, automatic or manually overridden one/three-phase kW
  regulation, battery-flow
  protection, and either a Zoe SOC target or a generic energy target. The
  charger-specific 6-32 A command conversion stays internal. Charger, solar,
  battery, solar production, vehicle SOC, and price entities are selected in
  integration options. Measurement and status sources can be left empty.
- Optional automatic Renault Trips dashboard with day selection, route maps,
  speed samples, distance, and estimated energy consumption.
- Separate mileage dashboard view with daily totals, odometer-based paved and
  gravel/unpaved distance, unknown-surface coverage, and approximate average
  and maximum route speeds.
- Matching full-screen Charging and IMMAX views with responsive controls,
  configurable history periods, calendar dates, and large interactive charts.
- Server-side IMMAX **Charge now** and **Delay 12 h** command sequences start
  at 6 A and use Tuya Local only. The controls are disabled while the local
  charger connection is unavailable.

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
Open **Zoe New Extended > Configure > Renault smart charging** to select the
planner's Nord Pool country, targets, price cap, and allowed zones. Use
**Energy cost model** for delivery price, VAT, usable capacity, efficiency, and
fallback consumption. **IMMAX setpoints** stores the charger controller limits
and synchronizes them to the included helpers. Use **IMMAX entity sources** to
select the charger controls, phase measurements, grid export, battery flow,
solar production, vehicle SOC, and price entities. Charger control and current
are required; every measurement or status source can be left empty and is then
excluded. Two global switches expose the location guard
and unrestricted-location option without duplicating every zone as a device
switch.

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

## IMMAX Smart Charger

The optional files in [`immax_smart_charger`](immax_smart_charger) provide
Nord Pool scheduling and dynamic one- or three-phase solar-surplus regulation
for the IMMAX Tuya EV charger. The two modes are mutually exclusive and `Off`
preserves manual charger control. The supplied card shows calculated planner
and solar values as read-only sensors; only actual settings remain editable.

Read [`immax_smart_charger/README.md`](immax_smart_charger/README.md), select
the source entities in the integration options, and verify their live values
before enabling either smart mode.

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
