# testomatic-io

A Python hardware abstraction layer for the I/O features of the 
[Testomatic](https://testomatic.io/) PCB test system chassis and its test 
modules.

## Overview

The Testomatic hardware is two distinct physical devices:

- **Chassis** — the fixed enclosure: IOMOD I/O expander modules (behind a
  TCA9548A I2C multiplexer), the 3.3V/5V/12V power rail relays and INA260
  sensors, the IOMOD interrupt line, the external "test start" button, the
  piezo beeper, and the chassis's own identity EEPROM.
- **Test Module** — a swappable shim that plugs into the chassis to
  interface with a specific Device Under Test. Today that's just its
  identity EEPROM; more Test-Module-specific hardware and drivers will be
  added over time, varying per Test Module type.

`testomatic_io.Chassis` and `testomatic_io.TestModule` are the two top-level
entry points, each grouping its subsystems into sub-namespaces:

```python
from testomatic_io import Chassis, TestModule

chassis = Chassis()
chassis.init()

test_module = TestModule()
test_module.init()

chassis.iomod.digital_write('C', 4, True)
chassis.power.rail_3v3(True)
chassis.power.read_3v3()          # PowerReading(voltage, current, power)
chassis.interrupts.is_asserted()
chassis.button.pressed()
chassis.beeper.beep(0.1)
chassis.hat_eeprom.read(0, 32)

test_module.eeprom.read(0, 32)
```

## Features

- **IOMODs**: multiple ADC/DAC/GPIO expander modules behind a TCA9548A
  multiplexer, with the expander chip on each module identified
  automatically by its I2C address — no manual configuration needed
- **Power rails**: turn the 3.3V/5V/12V rails to the Device Under Test on or
  off, and measure voltage/current/power on each via INA260 sensors
- **IOMOD interrupts**: read the shared interrupt line that all IOMODs OR
  onto
- **Button**: read the external "test start" button
- **Beeper**: drive the piezo beeper
- **EEPROMs**: read/write the chassis identity EEPROM and the Test Module
  identity EEPROM (both CAT24C32, on I2C bus 0)

Not yet implemented: thermal camera capture (planned, MLX90640 over serial),
and Test-Module-specific drivers beyond the identity EEPROM.

## Supported IOMOD Expander Chips

- **AD5593R** — 8-channel ADC/DAC/GPIO, I2C address `0x10`

Support for additional chips (e.g. MCP23008, Serial Wombat) can be added by
writing a driver — see [testomatic_io/iomod/drivers/](testomatic_io/iomod/drivers/)
for the driver interface and the AD5593R driver as a reference implementation.

## Hardware Requirements

- Raspberry Pi (or other Blinka-supported board)
- TCA9548A I2C multiplexer, on I2C bus 1
- One or more IOMOD modules (connected via the multiplexer), each fitted
  with a supported expander chip
- 3× INA260 power monitors on I2C bus 1 (not behind the multiplexer):
  3.3V rail at `0x42`, 5V rail at `0x41`, 12V rail at `0x40`
- 2× CAT24C32 I2C EEPROMs on I2C bus 0: chassis identity at `0x50`,
  Test Module identity at `0x51`
- See [testomatic_io/pinout.py](testomatic_io/pinout.py) for the full GPIO
  pin map (power rail relays, button, beeper, IOMOD interrupt line)

## Dependencies

```bash
pip install -r requirements.txt
```

or for local development:

```bash
pip install -e .
```

`import testomatic_io` requires actual Raspberry Pi (or other
Blinka-supported) hardware — `board`/Adafruit-Blinka does platform detection
at import time and raises `NotImplementedError` on unsupported platforms
(e.g. a Mac dev machine). When working on this repo without hardware, verify
logic by stubbing `board`, `adafruit_tca9548a`, `digitalio`, and `busio` with
fakes before importing `testomatic_io`, rather than trying to run it
directly.

## Quick Start

```python
from testomatic_io import Chassis

chassis = Chassis()
chassis.init()

# Scan for available IOMODs
modules = chassis.iomod.scan_modules()
print(f"Available modules: {modules}")

# Write HIGH to pin 4 on module D
chassis.iomod.digital_write('D', 4, True)

# Read from pin 1 on module C
value = chassis.iomod.digital_read('C', 1)

# Read analog voltage from pin 3 on module B
voltage = chassis.iomod.read_voltage('B', 3)

# Turn on the 3.3V rail and read it back
chassis.power.rail_3v3(True)
reading = chassis.power.read_3v3()
print(f"3.3V rail: {reading.voltage:.3f}V, {reading.current:.1f}mA, {reading.power:.0f}mW")
```

Modules can be referenced either by letter (`'A'`-`'H'`, preferred) or by their
underlying numeric channel (`0`-`7`) on the TCA9548A multiplexer.

## API Reference

### Chassis

```python
chassis.init(i2c_bus=None, i2c_bus0=None)
```
Initialize every chassis subsystem. `i2c_bus` is bus 1 (IOMODs + power
sensors), defaulting to `board.I2C()`. `i2c_bus0` is bus 0 (the identity
EEPROM bus) — pass the same object to `TestModule.init()` if using both
together, so they share one bus 0 connection.

#### `chassis.iomod` — IOMODs

```python
chassis.iomod.scan_modules()
```
Scan for available modules and return a list of working module letters
(`'A'`-`'H'`). Each module's expander chip is identified automatically by
its I2C address.

```python
chassis.iomod.select_module(module_id)
```
Validate that a module is present and ready for use.

```python
chassis.iomod.digital_write(module_id, pin, value)
chassis.iomod.digital_read(module_id, pin)
chassis.iomod.toggle(module_id, pin)
```
Digital I/O: write/read HIGH/LOW, or toggle an output pin.

```python
chassis.iomod.analog_read(module_id, pin, average=1)
chassis.iomod.analog_write(module_id, pin, value)
chassis.iomod.read_voltage(module_id, pin, average=1)
```
Analog I/O: raw ADC value (0-4095), raw DAC value (0-4095), or voltage in
volts (chip-dependent).

```python
chassis.iomod.pin_mode(module_id, pin, mode)
```
Configure pin mode: `testomatic_io.INPUT`, `OUTPUT`, `ADC`, or `DAC`.

```python
chassis.iomod.set_vref(module_id, activate=True)
chassis.iomod.get_vref(module_id)
chassis.iomod.get_dac_range(module_id)
chassis.iomod.set_dac_range(module_id, range=2)
chassis.iomod.set_ldac_mode(module_id, mode)
```
Voltage reference and DAC range management (chip-dependent).

```python
chassis.iomod.reset(module_id)
```
Reset the specified module.

#### `chassis.power` — power rails

```python
chassis.power.rail_3v3(on)
chassis.power.rail_5v(on)
chassis.power.rail_12v(on)
```
Turn a power rail relay on or off.

```python
chassis.power.rail_3v3_enabled()
chassis.power.rail_5v_enabled()
chassis.power.rail_12v_enabled()
```
Read back whether a rail relay is currently on.

```python
chassis.power.read_3v3()
chassis.power.read_5v()
chassis.power.read_12v()
```
Read a rail's INA260 sensor. Returns a `PowerReading(voltage, current, power)`
namedtuple — voltage in V, current in mA, power in mW.

#### `chassis.interrupts`

```python
chassis.interrupts.is_asserted()
```
True if any IOMOD has a pending interrupt (the shared line is driven low).
Doesn't identify which module — poll `chassis.iomod`'s modules to find it.

#### `chassis.button`

```python
chassis.button.pressed()
```
True while the external button is held down.

#### `chassis.beeper`

```python
chassis.beeper.on()
chassis.beeper.off()
chassis.beeper.beep(duration_s=0.1)
```
Drive the piezo beeper.

#### `chassis.hat_eeprom`

```python
chassis.hat_eeprom.read(address, length)
chassis.hat_eeprom.write(address, data)
```
Read/write the chassis identity EEPROM (CAT24C32 at `0x50`, I2C bus 0).

### TestModule

```python
test_module.init(i2c_bus0=None)
```
Initialize the Test Module. `i2c_bus0` is bus 0 — pass the same object as
`Chassis.init()`'s if using both together.

```python
test_module.eeprom.read(address, length)
test_module.eeprom.write(address, data)
```
Read/write the Test Module identity EEPROM (CAT24C32 at `0x51`, I2C bus 0).

## Constants

- `testomatic_io.HIGH` / `LOW` — digital states (1 / 0)
- `testomatic_io.INPUT` / `OUTPUT` / `ADC` / `DAC` — IOMOD pin modes

## Adding a New IOMOD Expander Driver

To support a new I/O expander chip:

1. Create a driver module in `testomatic_io/iomod/drivers/` that subclasses
   `ExpanderDriver` (see `testomatic_io/iomod/drivers/base.py` for the
   interface and `testomatic_io/iomod/drivers/ad5593r.py` for a reference
   implementation).
2. Implement `probe(i2c_adapter, address)` as a classmethod that returns
   `True` when the driver recognises a chip at that address — matching on
   address alone is fine for chips with a fixed or narrow address range;
   chips that could share an address with another supported device should
   read an identifying register instead.
3. Implement the operations the chip actually supports (`pin_mode`,
   `digital_write`, `digital_read`, `toggle`, and where applicable
   `analog_read`, `analog_write`, `read_voltage`, `set_vref`, `get_vref`,
   `get_dac_range`, `set_dac_range`, `set_ldac_mode`, `reset`). Operations a
   chip doesn't support can be left unimplemented — the base class raises
   `NotImplementedError` for them.
4. Register the class in `DRIVERS` in `testomatic_io/iomod/drivers/__init__.py`.

Once registered, modules using that chip are detected and used automatically
— no changes to `IOModManager` itself are needed.

## Running Examples

### Basic Example
```bash
python examples/testomatic_io_example.py
```

### Interactive Mode
```bash
python examples/testomatic_io_example.py interactive
```

The interactive mode provides a command-line interface for testing
individual functions.

## Error Handling

- **Invalid module**: Must be a letter A-H or number 0-7
- **Invalid pin number**: Must be 0-7
- **Invalid pin mode**: Must be INPUT, OUTPUT, ADC, or DAC
- **No supported expander found**: No registered driver recognised a chip on
  that module's I2C channel
- **Module not found**: Module not responding on I2C bus
- **I2C errors**: Communication failures
- **Unsupported operation**: A chip-dependent operation (e.g. analog I/O)
  not supported by the expander on that module

## Notes

- IOMOD modules are referenced by letter A-H (preferred) or by their
  underlying numeric channel 0-7 (TCA9548A has 8 channels)
- IOMOD pin numbers range from 0-7 (matching the AD5593R's 8 I/O pins; other
  supported chips may differ)
- ADC/DAC values are 12-bit (0-4095) on the AD5593R
- Voltage reference is typically 2.5V or 5V depending on configuration
- Not every expander chip supports every operation — GPIO-only chips will
  raise `NotImplementedError` for analog/voltage-reference calls
- `Chassis` and `TestModule` are independent top-level classes, not nested,
  since they represent two separate physical devices with independent
  lifecycles (a Test Module can be swapped without reinitializing the
  chassis)
