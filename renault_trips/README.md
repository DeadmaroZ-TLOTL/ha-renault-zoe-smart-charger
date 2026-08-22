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
   views. `stations.html` provides the Elektrum Drive, Mobilly, e-mobi,
   Latvia National Access Point, Ignitis ON, IKRAUTAS, and PlugShare map.
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
visual system, Latvian/English labels, and a persisted period selector. It
offers today, 3/7/14/30/90 calendar days, the current month, all available
history, or an inclusive custom **From/To** date range. Charging sessions,
trips, mileage, costs, and chart history follow that selected range. Chart
lines stop across missing Recorder samples instead of drawing misleading
connections. On narrow screens each panel uses the full viewport width and the
control columns stack vertically.

## Charging stations

The Stations view combines complete Elektrum Drive, Mobilly, e-mobi, Latvia
National Access Point, Ignitis ON, and IKRAUTAS catalogs and centers the map on
the Renault location when it is available. The NAP DATEX II feed supplies
country-wide connector details, live status, and tariffs every 15 minutes.
Source metrics show the raw catalog count beside the unique physical-station
count. The nearby list starts with 40 rows for performance and can expand to
every filtered station. Search,
provider, plug-type, minimum-power, and known-availability filters run locally
in the browser. Selecting a station shows every known connector, its physical
number, operator price, provider description/access notes, and live state when
the provider exposes it. The nearest-cheapest action accepts a maximum distance
and respects the active provider, plug, power, availability, and operator
filters; zero or unknown prices are excluded and per-kWh prices are never mixed
with per-minute prices. Directions open in Google Maps or Waze, and the
WhatsApp action opens a prefilled station location message for the user to
send. A separate provider tab embeds the public PlugShare map; PlugShare
locations are not merged into the local catalog because PlugShare declined API
access for this use case. Matching source rows are merged by EVSE identifier or
conservative physical-location checks. Each provider's independent price,
status, description, and complete connector set remains available.

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

The daily chart keeps EUR/100 km as its comparable scale and shows the exact
daily EUR total, distance, and average in its pointer tooltip. Daily aggregates
are merged into the authenticated Zoe New Extended cost-history store. This
preserves closed months after Recorder cleanup and feeds a monthly history
table plus a dedicated current-month EUR/100 km metric. The separate
**Charged in period** metric deliberately mirrors the Charging tab's grid kWh
and session cost. **Spent on trips** is different by design: it values only the
battery energy consumed while driving, including energy charged before the
selected period.

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
