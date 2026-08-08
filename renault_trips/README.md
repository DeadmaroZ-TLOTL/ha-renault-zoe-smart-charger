# Renault Trips

This folder contains the Renault Trips page used by the included Home Assistant
dashboard. It builds trips automatically from Home Assistant Recorder history;
there are no manual start or stop controls and no separate trip database.

## Required entities

The default page expects:

| Purpose | Entity |
| --- | --- |
| Position | `device_tracker.location` |
| Odometer | `sensor.mileage` |
| Battery SOC | `sensor.battery` |
| Remaining range | `sensor.battery_autonomy` |
| Charge state | `sensor.charge_state` |
| Plug state | `sensor.plug_state` |
| Charging | `binary_sensor.charging` |
| Climate | `binary_sensor.hvac` |

Change the `ENTITY` object near the top of the scripts in
`www/renault_trips/index.html` and `www/renault_trips/mileage.html` if your
Renault entity IDs differ.

## Install

1. Copy the contents of `www/renault_trips/` to
   `/config/www/renault_trips/`. `control.html`, `control-pages.css`, and
   `control-pages.js` provide the matching full-screen Charging and IMMAX
   views. `stations.html` provides the Elektrum Drive, Mobilly, e-mobi, and
   PlugShare map.
2. Install ApexCharts Card 2.2.3 or newer through HACS. The complete dashboard
   plots every known Nord Pool interval from today and tomorrow together with
   the price-cap line.
3. Add the panel views from `dashboard_view.yaml` and `mileage_view.yaml` to a
   Lovelace dashboard.
4. Keep Recorder history enabled for the position, odometer, and battery
   entities.

`dashboard.json` is the complete dashboard export used by this
project. It also expects the Zoe New Extended integration and the smart charger
package from the repository root. `charge_sessions_card.md.jinja` is the full
existing charge-session card used by that dashboard.

## Dashboard views

Charging, Trips, Mileage, Costs, Info, Stations, and IMMAX share one responsive
visual system and Latvian/English labels. Charging and IMMAX include full-width
history charts, current-value controls, and 24-hour, 48-hour, 7-day, 30-day, or
calendar-date history selection. Chart lines stop across missing Recorder
samples instead of drawing misleading connections. On narrow screens each
panel uses the full viewport width and the control columns stack vertically.

## Charging stations

The Stations view combines Elektrum Drive, Mobilly, and e-mobi catalogs and
centers the map on the Renault location when it is available. Search,
provider, plug-type, minimum-power, and known-availability filters run locally
in the browser. Selecting a station shows every known connector, its physical
number, operator price, and live state when the provider exposes it. Directions
open in Google Maps or Waze, and the WhatsApp action opens a prefilled station
location message for the user to send. A separate provider tab embeds the
public PlugShare map; PlugShare locations are not merged into the local catalog
because its station-data API requires a commercial license.

## Energy cost model

The `Cenas` view has a persistent Latvian/English language selector and
maintains a chronological weighted-average battery cost model.
Each Renault charge session adds its SOC-derived battery energy and calculated
grid cost including delivery. Each detected trip removes its battery energy at
the weighted unit cost that applied before the trip, producing trip cost and
EUR/100 km statistics. The current battery energy and value are reconciled to
the latest reported SOC. Usable capacity, charging efficiency, delivery price,
VAT, and fallback consumption come from the Zoe New Extended integration
options. Sessions with incomplete price coverage and trips with missing or
implausible SOC movement are shown as estimates rather than being treated as
free energy.

## How trips are calculated

The page reads the selected day or period from Home Assistant history, groups
position changes into trips, and reconciles GPS distance with odometer changes.
GPS-only movements below 0.75 km are ignored as location jitter. Nearby trips
are grouped when Renault's delayed SOC samples cannot reliably distinguish
their individual energy use; the group's 52 kWh battery reduction is allocated
by distance. Each row shows the resulting approximate SOC change, energy, and
consumption. Leaflet renders the map and the public OSRM service reconstructs
road routes and five-second speed samples. Route results are cached only in the
browser.

## Mileage and road surface

The `Nobraukums` view groups the same automatically detected trips by day and
shows total distance split into paved, gravel/unpaved, and unknown road
surface. The page map-matches cached OSRM routes with the public Valhalla
service and uses OpenStreetMap surface tags. Surface distances are scaled to
the odometer-based trip distance. Missing or ambiguous map data stays unknown
instead of being guessed, and results are cached in the browser. The summary
and trip table also show approximate average speed derived from OSRM route
annotations; it is a route estimate rather than vehicle telemetry. Selecting
a colored bar under **Nobraukums pa dienām** expands that day's exact paved,
gravel/unpaved, and unknown-surface kilometer totals.
