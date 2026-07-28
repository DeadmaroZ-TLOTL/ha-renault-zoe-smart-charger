# IMMAX Smart Charger

This optional Home Assistant package adds two mutually exclusive control modes
for an IMMAX three-phase Tuya EV charger:

- **Nord Pool** selects the cheapest eligible 15-minute intervals before the
  configured deadline. It supports a maximum spot price, a Zoe SOC target, or
  a generic energy target for another vehicle.
- **Solar surplus** continuously adjusts charging between the configured
  minimum and maximum power in kW. It uses grid export plus battery net
  charging and adds the charger's existing load back into the control signal.
  This avoids the feedback loop that would otherwise reduce charging power as
  soon as the charger starts.

Solar control automatically detects whether one or three phases are available
from the charger phase-voltage sensors. A phase is considered present when its
voltage remains between 180 and 260 V. The controller confirms three-phase
operation after 8 stable seconds and one-phase operation after 20 stable
seconds, avoiding false changes during startup. If no complete one- or
three-phase pattern is available, it retains the last valid mode. Detection
changes the power calculation; it does not physically switch charger phases.
The card's phase selector defaults to **Auto**. Select **1 phase** or
**3 phases** to override the detected result manually; detection continues in
the background so returning to **Auto** immediately uses the current result.

The nominal electrical limits are 1.4-7.4 kW for one phase and 4.2-22 kW for
three phases. User-configured minimum and maximum power limits are preserved
when the detected phase count changes; the controller always enforces the
electrical minimum for the detected mode.

The modes share one selector, so they cannot issue conflicting commands. `Off`
leaves the charger under manual control. Moving from a smart mode to `Off`
stops the active smart session once and then restores manual operation.

## Solar control signal

When grid export or either battery-flow source is selected, the package
calculates net available power as:

```text
charger power + grid export + battery charging - battery discharging - reserve
```

Each selected flow source contributes independently, so battery charging and
discharging still control the available surplus when grid export is left
empty. If solar production is also selected, it caps that result so the
requested charging power cannot exceed current PV production plus any
explicitly allowed battery support. A positive reserve leaves that much power
available for the battery or grid; a negative reserve permits the charger to
draw up to its absolute value beyond the available solar power. If every flow
source is empty, solar production becomes the direct fallback source. Every
optional source may be left empty and then contributes nothing; charger
control and current remain required. Power sources may report either W or kW.

All solar settings and reported values use kW. Home Assistant requests fresh
load, SOC, charger, solar, grid, and battery-flow states every 15 seconds. The
controller evaluates them every 15 seconds and whenever a selected source
changes.
Charging starts when the result can sustain the configured minimum power or
the electrical 6 A minimum, whichever is higher. Every new session explicitly
sets the twelve-hour Delay mode, applies 6 A, and only then changes to Immediate.
It holds 6 A for the first 30 seconds so the vehicle and power-flow sensors can
settle. The charging switch is never used by smart control.

Because the charger protocol accepts only whole-ampere commands, Home Assistant
converts the requested kW internally using the measured three-phase voltage. In
one-phase mode it uses the average measured phase voltage instead. The internal
command is limited to 6-32 A and then changes by one ampere at a time, no more
often than every 15 seconds. If available power falls below the minimum, the
controller first returns to 6 A and waits for 30 seconds. It pauses charging by
selecting the maximum twelve-hour Delay only if power is still insufficient.
The next start selects Immediate without toggling the charging
switch, allowing a vehicle that ended the previous session to resume reliably.
Some charger firmware takes about two minutes to stop after accepting Delay.
The included enforcer repeats the local Delay command every 30 seconds while
phase current still confirms that charging is active. Delay writes the local
charge schedule with a start time twelve hours ahead before selecting
`delayed_charge`; Immediate clears that schedule before selecting `immediate`.
Transient `unknown` or `unavailable` charger states do not trigger commands.

Both smart modes also enforce the editable total AC power limit, which defaults
to 3.5 kW, using `sensor.renault_zoe_new_immax_total_site_load`. Select the real
site electricity meter in the integration's **IMMAX entity mapping** options.
The controller adjusts its
current from the measured total-load headroom. Current is reduced immediately,
while increases happen one ampere at a time and wait for a new total-load
measurement after every charger mode or current change. If even 6 A would
exceed the limit, or if the total-load meter is unavailable, automatic charging
selects the twelve-hour Delay mode. `Off` continues to mean fully manual
control.

The configured meter source is exposed through
`sensor.renault_zoe_new_immax_total_site_load` and is expected to report power. In
this installation it points to the Tuya Local meter source. A similarly named
Tuya cloud entity is not used for the safety limit.

The stationary battery guard reads `sensor.unibms_soc`. Its editable defaults
pause smart charging at 50% and keep it in the twelve-hour Delay mode until the
battery reaches 60%. The separate stop and resume values provide hysteresis, so
charging cannot repeatedly start and stop between the two thresholds. If the
resume value is set at or below the stop value, the guard automatically moves
it to one percentage point above the stop value. An unavailable SOC source
retains the current hold state instead of unexpectedly resuming charging.

The optional AI advisor uses the already configured
`ai_task.google_ai_task_2` provider. It receives a compact snapshot at the
editable interval, which defaults to 15 minutes, and must return structured
`KEEP`, `LIMIT`, or `PAUSE` data. AI can only lower the current cap or request a
pause; it cannot raise the deterministic result, bypass the total-power or SOC
guards, or send charger commands directly. If the token-backed AI provider
fails, its pause and cap are cleared and the local 15-second controller
continues independently.

## Installation

1. Enable Home Assistant packages in `configuration.yaml`.
2. Copy `immax_smart_charger_package.yaml` into the packages directory.
3. Install or update Zoe New Extended to version 1.9.8 or newer.
4. Restart Home Assistant.
5. Open **Settings > Devices & services > Zoe New Extended > Configure >
   IMMAX entity sources** and select the entities used by the controller.
   Leave any unused measurement or status source empty.
6. Add `lovelace_card.yaml` as a manual card or as its own dashboard view.
   `lovelace_statistics_cards.yaml` adds the matching statistics cards.

The integration publishes stable proxy entities, so changing a selected source
does not require editing the package or card. The source values must use these
sign conventions:

- Grid export is positive while power is sent to the grid.
- Battery charging and discharging are separate positive values.
- Phase power, current, and voltage entities report each charger phase.

The card keeps target, deadline, smart mode, phase override, reserve, total AC
power limit, battery SOC stop/resume thresholds, and charging limits editable.
Detected phase mode, calculated status, planned energy, estimated cost,
available solar power, target power, actual charger power, grid export, battery
flow, battery SOC, and the compact AI recommendation are exposed as read-only
values. Selecting a sensor row opens Home Assistant's standard more-info dialog
with its recorded history.

The supplied statistics cards add a live six-value charging summary, 24-hour
charging and total-load power history, daily charged-energy bars for the last
14 days, seven-day stationary-battery SOC history, and 24-hour phase-current
history. They use Home Assistant recorder statistics and require no external
chart card.
