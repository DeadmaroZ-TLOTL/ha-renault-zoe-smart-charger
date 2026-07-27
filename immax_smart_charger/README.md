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

Solar control can use either a one-phase or three-phase power model. The
nominal limits are 1.4-7.4 kW for one phase and 4.2-22 kW for three phases.
Changing this option changes the control calculation; it does not physically
switch charger phases unless the installation has separate phase-switching
hardware.

The modes share one selector, so they cannot issue conflicting commands. `Off`
leaves the charger under manual control. Moving from a smart mode to `Off`
stops the active smart session once and then restores manual operation.

## Solar control signal

The package calculates available power as:

```text
charger power + grid export + battery charging - battery discharging - reserve
```

All solar settings and reported values use kW. Charging starts only when the
result can sustain the configured minimum power plus a 0.5 kW start margin.
Because the charger protocol accepts only whole-ampere commands, Home Assistant
converts the requested kW internally using the measured three-phase voltage.
In one-phase mode it uses the average measured phase voltage instead. The
internal command is limited to 6-32 A and changes by at most 2 A per adjustment.
Commands are spaced by at least 45 seconds, and low-surplus shutdown has a
two-minute guard.

## Installation

1. Enable Home Assistant packages in `configuration.yaml`.
2. Copy `immax_smart_charger_package.yaml` into the packages directory.
3. Check every entity ID listed at the top of the package.
4. Restart Home Assistant.
5. Add `lovelace_card.yaml` as a manual card.

The supplied defaults match the author's installation. In particular,
`sensor.solax_srd9cccxv6_feed_in_power` must be positive while exporting, and
the UniBMS `battery_in` / `battery_out` sensors must report positive watts.
