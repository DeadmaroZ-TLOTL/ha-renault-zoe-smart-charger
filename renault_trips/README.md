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

1. Copy `www/renault_trips/index.html` and
   `www/renault_trips/mileage.html` to `/config/www/renault_trips/`.
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
and trip table also show approximate average and maximum speeds derived from
OSRM route annotations; these are route estimates rather than vehicle
telemetry.
