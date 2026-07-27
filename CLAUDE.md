# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

testomatic-io is a Python hardware abstraction layer for the I/O features of
the Testomatic chassis, typically on a Raspberry Pi. The Testomatic hardware
is two distinct physical devices, each with its own top-level facade class:

- **`Chassis`** (`testomatic_io/chassis.py`) — the fixed enclosure: IOMOD I/O
  expander modules behind a TCA9548A I2C multiplexer, the 3.3V/5V/12V power
  rail relays and INA260 sensors, the IOMOD interrupt line, the external
  button, the piezo beeper, and the chassis's own identity EEPROM.
- **`TestModule`** (`testomatic_io/test_module.py`) — a swappable shim that
  plugs into the chassis to interface with a specific Device Under Test.
  Currently just its identity EEPROM; expected to grow per-DUT-type drivers
  over time. Deliberately kept as an independent top-level class (not
  `chassis.test_module`) so it can be split into its own package later
  without restructuring `Chassis`.

Each facade groups its subsystems into sub-namespaces (`chassis.iomod`,
`chassis.power`, `chassis.interrupts`, `chassis.button`, `chassis.beeper`,
`chassis.hat_eeprom`, `test_module.eeprom`) rather than exposing one flat set
of methods — see `README.md` for the full API.

## Commands

There is no test suite, linter, or CI configured yet.

```bash
# Editable install for local development (pulls in adafruit-blinka, tca9548a driver, etc.)
pip install -e .

# Or from requirements.txt directly
pip install -r requirements.txt

# Run the example script against real hardware
python examples/testomatic_io_example.py
python examples/testomatic_io_example.py interactive
```

`import testomatic_io` requires actual Raspberry Pi (or other Blinka-supported) hardware — `board`/Adafruit-Blinka does platform detection at import time and raises `NotImplementedError` on unsupported platforms (e.g. a Mac dev machine). When working on this repo without hardware, verify logic by stubbing `sys.modules['board']`, `sys.modules['adafruit_tca9548a']`, `sys.modules['digitalio']`, and `sys.modules['busio']` with fakes before importing `testomatic_io`, rather than trying to run it directly.

## Architecture

### IOMOD subsystem (`chassis.iomod`, an `IOModManager`)

#### Module addressing

Modules are referenced by letter (`'A'`-`'H'`, preferred) or by numeric TCA9548A channel (`0`-`7`); `testomatic_io/iomod/manager.py`'s `_module_index`/`_module_letter` convert between the two, and `IOModManager._validate_module_id` normalizes any call's `module_id` to the numeric form before use. `scan_modules()` returns letters.

#### Driver abstraction (the core design)

Expander chip support is pluggable so new chip types can be added without touching `IOModManager`:

- `testomatic_io/iomod/drivers/base.py` — `ExpanderDriver`, the interface every chip driver implements: `pin_mode`, `digital_write`/`digital_read`, `toggle`, `analog_read`/`analog_write`, `read_voltage`, `set_vref`/`get_vref`, `set_dac_range`/`get_dac_range`, `set_ldac_mode`, `reset`, plus a `probe(i2c_adapter, address)` classmethod used for auto-detection. Operations a chip doesn't support are left unimplemented and raise `NotImplementedError` via the base class.
- `testomatic_io/iomod/drivers/__init__.py` — `DRIVERS`, the ordered list of registered driver classes, and `identify_driver(i2c_adapter, addresses)`, which checks each I2C address found on a module's channel against each driver's `probe()`.
- `testomatic_io/iomod/drivers/ad5593r.py` — `AD5593RDriver`, the reference implementation, at I2C address `0x10`.
- `testomatic_io/iomod/manager.py`'s `IOModManager._get_module()` scans a module's channel (`ChannelI2CAdapter.scan()`), calls `identify_driver()`, and instantiates whichever driver matches — no chip type is ever hardcoded. `scan_modules()` does the same per channel to report which modules are populated.

To add a new chip (e.g. MCP23008, Serial Wombat): write a driver module implementing the subset of `ExpanderDriver` that chip supports, and add its class to `DRIVERS` in `testomatic_io/iomod/drivers/__init__.py`. See `README.md`'s "Adding a New IOMOD Expander Driver" section.

This same shape of problem — "many drivers, auto-detected, chosen per unit" — is expected to recur for `TestModule` as it grows per-DUT-type drivers, likely keyed off an identifier read from the Test Module EEPROM. Not built yet; flagged here as the probable extension point.

#### The AD5593R driver wraps the published `ad5593r` PyPI package

`testomatic_io/iomod/drivers/ad5593r.py` delegates the AD5593R register-level protocol to the `ad5593r` package (`>=0.3.0`, pinned in `pyproject.toml`/`requirements.txt`) instead of reimplementing it in-house, which is how this driver worked until this migration. That was only possible once the package accepted an injectable I2C transport — `AD5593R(device_address, i2c_bus=..., bus_number=1)`, added upstream in the sibling repo `../ad5593r` (source of the PyPI package, at `/Users/jon/src/ad5593r`) — so its `i2c_bus` can be handed `ChannelI2CAdapter` directly and routed through the TCA9548A multiplexer's per-channel addressing. Before that, the published package always opened its own `smbus2.SMBus(bus_number)` scoped to a Linux bus number, with no way to route it through the mux, which is why the earlier in-house implementation (ported from `old/ad5593r/ad5593r_library.py`) existed at all.

The package's `pin_mode(pin, mode)` (added in its own v0.3.0) handles single-pin function configuration; `AD5593RDriver` layers on top of it for the parts the package doesn't expose as a single call — activating the internal Vref and setting ADC/DAC range whenever a pin is configured as `ADC`/`DAC` (see `pin_mode()`), and tracking the chip-wide DAC range itself since the package has no getter for it (see `_dac_range` in `__init__`).

This same reuse-over-reimplement approach was followed for the two new I2C-based subsystems added in the `testomatic-io` restructure: `power/sensors.py`'s `PowerSensors` wraps the published `adafruit-circuitpython-ina260` package, and `eeprom.py`'s `Cat24C32` wraps the published `adafruit-circuitpython-24lc32` package (the Microchip 24LC32 is pin/protocol-compatible with the CAT24C32 chips actually fitted).

**The AD5593R migration changed real hardware behaviour, not just plumbing — see `old/ad5593r/DIAGNOSIS.md`.** The in-house implementation being replaced had a bug matching that file's hypothesis #4 ("Separate ADC/DAC Range Control... we're setting the wrong one"): it used the *ADC* range bit (bit 5 of the general-control register) for *both* `ADC()` and `DAC()` pin configuration, so `setDACRange()`/asking for 2x Vref on a DAC pin never actually changed DAC output range — it silently touched the ADC range bit instead. The `ad5593r` package correctly uses separate bits (`set_adc_range_2x()` = bit 5, `set_dac_range_2x()` = bit 4), confirmed by cross-checking the exact register/bit math against the old implementation before migrating. `AD5593RDriver.set_dac_range()`/`pin_mode(pin, DAC)` now use the package's `set_dac_range_2x()`, so DAC range control actually works — this should fix the symptom in `DIAGNOSIS.md`, but hasn't yet been re-verified against real hardware. The `setDACRange`/`getDACRange` debug prints that file asked to keep (see the `old/` section below) were removed as part of this fix, since the bug they were instrumented to chase is now understood and addressed rather than open.

#### I2C adapter layer

`ChannelI2CAdapter` in `testomatic_io/iomod/manager.py` wraps a CircuitPython `adafruit_tca9548a` channel object (which exposes `readfrom_into`/`writeto`) to provide the plain `readfrom`/`writeto`/`scan` interface that drivers expect, acquiring/releasing the channel's I2C lock around each call.

#### Shared constants

`testomatic_io/iomod/constants.py` holds `HIGH`/`LOW`/`INPUT`/`OUTPUT`/`ADC`/`DAC`. These live outside `manager.py` specifically so that `testomatic_io/iomod/drivers/*` can import them without a circular import (`manager.py` imports from `drivers`, so `drivers` can't import back from `manager.py`). `testomatic_io/iomod/__init__.py` re-exports them, and the top-level `testomatic_io/__init__.py` re-exports them again for access as `testomatic_io.HIGH`, etc.

### Non-IOMOD chassis subsystems

Unlike IOMODs, these are fixed, known hardware on fixed GPIO pins / I2C addresses for this specific chassis design (not swappable modules behind a mux), so none of them use the driver-plugin/auto-detection pattern above:

- `testomatic_io/pinout.py` — the single canonical map of GPIO pins and I2C addresses for the physical chassis wiring (relays, INA260 addresses, interrupt/button/beeper pins, EEPROM addresses). Change chassis wiring here, not scattered through subsystem modules.
- `testomatic_io/gpio.py` — thin `digitalio.DigitalInOut` setup helpers (`digital_output`/`digital_input`) shared by the relay/button/beeper/interrupt subsystems, plus `open_i2c_bus0()` for the I2C bus 0 connection shared by `Chassis.hat_eeprom` and `TestModule.eeprom`.
- `testomatic_io/power/` — `PowerRails` (GPIO relay control), `PowerSensors` (INA260, direct on I2C bus 1, **not** behind the mux), and `Power` (the `chassis.power` facade combining both per rail — `rail_3v3()`/`read_3v3()` etc., returning a `PowerReading(voltage, current, power)` namedtuple).
- `testomatic_io/interrupts.py` — `Interrupts.is_asserted()` reads the single GPIO pin that all IOMOD interrupts are OR'd onto (external pull-up, active-low). It only reports that *some* module needs servicing; identifying which one is left to the caller, by polling `chassis.iomod`'s modules.
- `testomatic_io/button.py` / `beeper.py` — straightforward GPIO input/output wrappers for the external button and piezo beeper.
- `testomatic_io/eeprom.py` — `Cat24C32`, shared by both `chassis.hat_eeprom` (0x50) and `test_module.eeprom` (0x51).

### Two I2C buses

Everything except the two EEPROMs lives on I2C bus 1 (`board.I2C()`, the same bus the TCA9548A mux and INA260 sensors are on). Both CAT24C32 EEPROMs are on I2C bus 0 (the Raspberry Pi's dedicated HAT ID EEPROM bus) instead. `Chassis.init()` and `TestModule.init()` both accept an optional pre-built `i2c_bus0=` handle so code using both together can share one bus 0 connection rather than each opening its own; `testomatic_io/gpio.py`'s `open_i2c_bus0()` is the default when none is supplied. The exact Blinka bus-0 pin names (`board.SCL0`/`board.SDA0`) haven't been confirmed against real hardware yet.

### `old/` directory

`old/ad5593r/` contains earlier, untracked (gitignored) working files, including the pre-refactor `ad5593r_library.py` that `AD5593RDriver` was originally ported from (before migrating to the `ad5593r` package — see above), and `DIAGNOSIS.md` documenting the DAC range bug that migration is believed to have fixed. This directory is not part of the installable package.

### Not yet implemented

Thermal camera capture (MLX90640 over serial, RPi GPIO14/15) is planned but was explicitly deferred out of the initial `testomatic-io` restructure — no stub module exists for it yet.
