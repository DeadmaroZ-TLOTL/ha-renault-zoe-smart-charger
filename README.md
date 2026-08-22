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
- Any number of Mobilly, Elektrum Drive, Ignitis ON, and IKRAUTAS accounts.
  Exact completed-session energy and cost are merged across Mobilly statements,
  Elektrum app transactions, and the Ignitis ON or IKRAUTAS app profile. One
  physical charge split into several Renault API rows is shown once, with the
  direct operator record preferred over reseller data. Previously synchronized
  exact records remain available during temporary login or provider failures,
  while the account status clearly reports that reauthentication is required.
  Optional private operator-receipt overrides can supply exact metered energy
  and charged cost when a provider account cannot expose live history; those
  values remain marked as operator data instead of calculated estimates.
- Historical home sessions use recorder prices first and fill missing intervals
  from the official Nord Pool day-ahead archive, including the configured VAT.
- One-time Elektrum postpaid-agreement linking in integration options. The
  personal code is sent directly to Elektrum over HTTPS for Smart-ID approval
  and is never stored by Home Assistant.
- Renault account sign-in in the same options menu. It uses Renault's official
  Home Assistant client and updates only the selected official Renault config
  entry; credentials and refreshed tokens are never copied into this helper.
- A responsive **Stations** map combining the complete Elektrum Drive, Mobilly,
  e-mobi, Latvia National Access Point, Ignitis ON, and IKRAUTAS catalogs, plus
  an embedded PlugShare map. The
  official NAP DATEX II feed adds country-wide connector inventory, live
  status, and VAT-inclusive tariffs refreshed every 15 minutes. It includes provider, plug-type,
  power, and availability filters; connector models and physical plug numbers;
  provider prices, station descriptions/access notes, and live state when
  available; Google Maps and Waze navigation; and WhatsApp sharing. Duplicate
  source rows are collapsed only at the physical-station level while every
  provider offer and connector remains available. Raw and unique source counts
  make incomplete catalogs visible, and the nearby list can expand to every
  filtered station. A
  configurable distance limit can select the nearest station with the lowest
  known comparable price while respecting the active filters.
- Extended entities are attached to the dedicated **Renault Zoe ... Zoe New
  API** source device. Existing entity IDs stay unchanged, and empty duplicate
  vehicle devices can be removed safely after registry reconciliation.
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
- Location-aware `sensor.immax_paeglisi_power` and
  `sensor.immax_paeglisi_energy` account for IMMAX charging at the home zone
  only. Charging performed elsewhere therefore cannot inflate the site's
  Home Assistant Energy total.
- Optional automatic Renault Trips dashboard with day selection, route maps,
  speed samples, distance, and estimated energy consumption.
- Separate mileage dashboard view with daily totals, odometer-based paved and
  gravel/unpaved distance, unknown-surface coverage, and approximate average
  and maximum route speeds.
- Matching full-screen Charging, Trips, Mileage, Costs, Info, Stations, and
  IMMAX views with responsive controls and one persisted history selector.
  Choose today, 3/7/14/30/90 calendar days, the current month, all available
  history, or an inclusive custom **From/To** date range. Charging sessions,
  trips, mileage, costs, and chart history follow the selected range.
- Server-side IMMAX **Charge now** and **Delay 12 h** command sequences start
  at 6 A and use Tuya Local only. The controls are disabled while the local
  charger connection is unavailable.

Immediate charging uses the normal X102VE start action, which also resumes a
car left in scheduled mode by the previous stop. Stopping uses the
same KCM charge-schedule action as MyRenault: it installs a one-minute schedule
24 hours ahead, which moves the vehicle out of instant charging. This is used
because both KCM `pause` and the legacy KCA `stop` action fail to stop this Zoe
in practice. The original delayed-start workaround is retained in
[renault-api pull request #2202](https://github.com/hacf-fr/renault-api/pull/2202)
for upstream discussion, while this integration uses the physically verified
schedule method.

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
fallback consumption. **Charging accounts** adds, edits, disables, or removes
multiple Mobilly, Elektrum Drive, Ignitis ON, and IKRAUTAS accounts. After
authenticating an Elektrum app account, use **Import linked Elektrum app
profile** with the complete `elektrumdrive://app/open` hand-off link from the
signed-in Elektrum app. The integration verifies that the profile has a
postpaid agreement and that its transaction endpoint is available before it
replaces the saved session. This is preferred over SMS login because a fresh
Drive-only SMS profile can be valid while still having no Elektrum agreement.
The app link is neither logged nor retained after its token, phone, and device
ID are stored in the Home Assistant config entry. The older **Link Elektrum
agreement** Smart-ID flow remains available for profiles where Elektrum offers
agreement enrollment. Personal codes are discarded immediately. Account
secrets are not exposed as entity attributes or saved in this repository.
Ignitis ON uses the official app's email/password OAuth flow. Home Assistant
sends the password directly to Ignitis over HTTPS, discards it immediately,
and stores only the renewable AMPECO session. IKRAUTAS additionally supports
the official Android app's Google `third-party` exchange. That one-time Google
access token must be issued to the IKRAUTAS Android client; a normal Google
OAuth or OAuth Playground token belongs to a different client and is rejected.
A one-time email link is also offered when the operator tenant enables it with
a non-zero lifetime.
Repeated setup attempts for the same operator identity are merged instead of
creating duplicate accounts.
All enabled charging accounts are refreshed once per hour. A provider name is
attached to a completed Renault session only when an exact app transaction or
receipt matches it. Station-tariff fallbacks remain visibly estimated and are
never presented as proof that the charge was paid through that operator.
**Renault account login** signs the selected official
Renault entry in again with country/locale, username, and password. It uses the
same Renault API client as Home Assistant Core and stores the resulting
credentials and token only in the official Renault entry.
**IMMAX setpoints** stores the charger controller limits
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

For Energy dashboard accounting, use `sensor.immax_paeglisi_energy` as the
IMMAX consumption statistic and `sensor.immax_paeglisi_power` as its power
sensor. Keep the raw whole-site electricity meter as a separate device without
an `included_in_stat` parent relationship; Home Assistant otherwise subtracts
the child device totals from that meter's displayed history.

## Renault Dashboard

The optional full-screen dashboard and its complete export are in
[`renault_trips`](renault_trips). Charging, Trips, Mileage, Costs, Info,
Stations, and the optional IMMAX view share one responsive visual system. Trips
are calculated from Recorder history and do not need manual start/stop buttons.
The Stations view uses authenticated integration API endpoints and must run
inside Home Assistant. PlugShare is displayed through its public embedded map
because PlugShare declined station-data API access for this use case. The local
catalog instead consumes Latvia's CC0 National Access Point
[infrastructure](https://transportdata.gov.lv/en/card/d8e419c3-1585-4666-9067-85712befd2c4)
and [live status/price](https://transportdata.gov.lv/en/card/a377a160-baa1-4b67-b4e8-6612cd289e22)
DATEX II feeds. Rotating download URLs are resolved from public metadata on
every refresh rather than stored in the integration.

Elektrum station details include live connector state and current public
tariff when the provider page is reachable. Ignitis ON and IKRAUTAS provide
public connector inventory, current state, and tariffs through their official
app catalogs; when an app account is connected, its authenticated roaming
catalog and exact completed-session history are used as well. Latvia NAP fills
provider gaps and is deduplicated by EVSE ID and
physical location. Mobilly exposes location,
connector model/count, and maximum power publicly; live Mobilly occupancy and
tariff require a mobile-app session and are marked unavailable rather than
guessed. Provider descriptions, access instructions, opening hours, and notes
are preserved when duplicate catalog entries are combined.

Read [`renault_trips/README.md`](renault_trips/README.md) for the expected
Renault entities and installation path.

## Notes

- Renault can accept a cloud command before the vehicle receives it. The
  command status sensor reports both API acceptance and later vehicle state.
- The stop workaround activates a one-minute weekly schedule 24 hours ahead.
  The next normal X102VE start command returns the car to instant charging.
  Renault KCM `pause` is accepted but does not stop this `X102VE`, and KCA `stop` is
  rejected as an invalid payload.
- Renault and the Renault diamond are trademarks of Renault Group. Brand
  images are the assets already maintained by Home Assistant Brands.
