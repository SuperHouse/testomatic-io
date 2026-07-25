# IOMod Library

A Python wrapper library for controlling multiple IOMOD I/O Expander Modules through a TCA9548A I2C multiplexer.

## Overview

The IOMod library provides a high-level interface for managing multiple ADC/DAC/GPIO modules connected through a TCA9548A I2C multiplexer. It allows you to easily select specific modules and perform digital and analog operations on them.

Each module can use a different I/O expander chip. The chip is identified automatically from the I2C address it responds at, so once a module is set up you never need to specify its type — `iomod.digitalwrite('C', 4, iomod.HIGH)` just works, whatever expander is on module C.

## Features

- **Module Selection**: Automatically manages TCA9548A multiplexer channels
- **Automatic Chip Detection**: Identifies the expander chip on each module by I2C address — no manual configuration needed
- **Digital I/O**: Read and write digital values to GPIO pins
- **Analog I/O**: Read ADC values and write DAC values (chip-dependent)
- **Pin Configuration**: Configure pins as INPUT, OUTPUT, ADC, or DAC
- **Voltage Reference Management**: Enable/disable and read reference voltage (chip-dependent)
- **Error Handling**: Comprehensive validation and error reporting
- **Module Scanning**: Automatically detect available modules

## Supported Expander Chips

- **AD5593R** — 8-channel ADC/DAC/GPIO, I2C address `0x10`

Support for additional chips (e.g. MCP23008, Serial Wombat) can be added by writing a driver — see [iomod/drivers/](iomod/drivers/) for the driver interface and the AD5593R driver as a reference implementation.

## Hardware Requirements

- TCA9548A I2C multiplexer
- One or more IOMOD modules (connected via I2C), each fitted with a supported expander chip
- Compatible I2C bus (e.g., Raspberry Pi I2C)

## Dependencies

```bash
pip install adafruit-circuitpython-tca9548a
pip install adafruit-circuitpython-board
```

## Quick Start

```python
import iomod

# Initialize the system
iomod.init()

# Scan for available modules
modules = iomod.scan_modules()
print(f"Available modules: {modules}")

# Write HIGH to pin 4 on module D
iomod.digitalwrite('D', 4, iomod.HIGH)

# Read from pin 1 on module C
value = iomod.digitalread('C', 1)

# Read analog voltage from pin 3 on module B
voltage = iomod.readvoltage('B', 3)
```

Modules can be referenced either by letter (`'A'`-`'H'`, preferred) or by their
underlying numeric channel (`0`-`7`) on the TCA9548A multiplexer.

## API Reference

### Initialization

```python
iomod.init(i2c_bus=None)
```
Initialize the IOMod system. If `i2c_bus` is None, uses `board.I2C()`.

### Module Management

```python
iomod.scan_modules()
```
Scan for available modules and return a list of working module letters (`'A'`-`'H'`). Each module's expander chip is identified automatically by its I2C address.

```python
iomod.select_module(module_id)
```
Select a specific module for operations (convenience function).

### Digital Operations

```python
iomod.digitalwrite(module_id, pin, value)
```
Write a digital value (HIGH/LOW) to a pin on the specified module.

```python
iomod.digitalread(module_id, pin)
```
Read a digital value from a pin on the specified module.

```python
iomod.toggle(module_id, pin)
```
Toggle a digital output pin on the specified module.

### Analog Operations

```python
iomod.analogread(module_id, pin, average=1)
```
Read a raw ADC value (0-4095) from a pin on the specified module.

```python
iomod.analogwrite(module_id, pin, value)
```
Write a DAC value (0-4095) to a pin on the specified module.

```python
iomod.readvoltage(module_id, pin, average=1)
```
Read voltage value in volts from a pin on the specified module.

### Pin Configuration

```python
iomod.pinmode(module_id, pin, mode)
```
Configure pin mode:
- `iomod.INPUT` - Digital input
- `iomod.OUTPUT` - Digital output  
- `iomod.ADC` - Analog input
- `iomod.DAC` - Analog output

### Voltage Reference

```python
iomod.setvref(module_id, activate=True)
```
Enable or disable voltage reference for the specified module.

```python
iomod.getvref(module_id)
```
Get voltage reference value for the specified module.

### Utility Functions

```python
iomod.reset_module(module_id)
```
Reset the specified module.

## Constants

- `iomod.HIGH` - Digital high state (1)
- `iomod.LOW` - Digital low state (0)
- `iomod.INPUT` - Pin mode: digital input (1)
- `iomod.OUTPUT` - Pin mode: digital output (2)
- `iomod.ADC` - Pin mode: analog input (3)
- `iomod.DAC` - Pin mode: analog output (4)

## Adding a New Expander Driver

To support a new I/O expander chip:

1. Create a driver module in `iomod/drivers/` that subclasses `ExpanderDriver` (see `iomod/drivers/base.py` for the interface and `iomod/drivers/ad5593r.py` for a reference implementation).
2. Implement `probe(i2c_adapter, address)` as a classmethod that returns `True` when the driver recognises a chip at that address — matching on address alone is fine for chips with a fixed or narrow address range; chips that could share an address with another supported device should read an identifying register instead.
3. Implement the operations the chip actually supports (`pin_mode`, `digital_write`, `digital_read`, `toggle`, and where applicable `analog_read`, `analog_write`, `read_voltage`, `set_vref`, `get_vref`, `get_dac_range`, `set_dac_range`, `set_ldac_mode`, `reset`). Operations a chip doesn't support can be left unimplemented — the base class raises `NotImplementedError` for them.
4. Register the class in `DRIVERS` in `iomod/drivers/__init__.py`.

Once registered, modules using that chip are detected and used automatically — no changes to `IOMod` itself are needed.

## Examples

### Basic Digital I/O

```python
import iomod

# Initialize
iomod.init()

# Configure pin 2 as output on module A
iomod.pinmode('A', 2, iomod.OUTPUT)

# Write HIGH
iomod.digitalwrite('A', 2, iomod.HIGH)

# Configure pin 1 as input on module A
iomod.pinmode('A', 1, iomod.INPUT)

# Read value
value = iomod.digitalread('A', 1)
print(f"Pin 1 reads: {'HIGH' if value else 'LOW'}")
```

### Analog Operations

```python
import iomod

# Initialize
iomod.init()

# Enable voltage reference
iomod.setvref('A', True)

# Configure pin 3 as ADC
iomod.pinmode('A', 3, iomod.ADC)

# Read voltage
voltage = iomod.readvoltage('A', 3)
print(f"Voltage: {voltage:.3f}V")

# Configure pin 4 as DAC
iomod.pinmode('A', 4, iomod.DAC)

# Write analog value (50% of full scale)
iomod.analogwrite('A', 4, 2048)
```

### Multiple Modules

```python
import iomod

# Initialize
iomod.init()

# Scan for modules
modules = iomod.scan_modules()

# Control multiple modules
for i, module_id in enumerate(modules):
    # Set pin 0 as output
    iomod.pinmode(module_id, 0, iomod.OUTPUT)

    # Write different states
    state = i % 2  # Alternate HIGH/LOW
    iomod.digitalwrite(module_id, 0, state)
    print(f"Module {module_id}: Pin 0 = {'HIGH' if state else 'LOW'}")
```

## Running Examples

### Basic Example
```bash
python iomod_example.py
```

### Interactive Mode
```bash
python iomod_example.py interactive
```

The interactive mode provides a command-line interface for testing individual functions.

## Error Handling

The library includes comprehensive error handling:

- **Invalid module**: Must be a letter A-H or number 0-7
- **Invalid pin number**: Must be 0-7  
- **Invalid pin mode**: Must be INPUT, OUTPUT, ADC, or DAC
- **No supported expander found**: No registered driver recognised a chip on that module's I2C channel
- **Module not found**: Module not responding on I2C bus
- **I2C errors**: Communication failures
- **Unsupported operation**: A chip-dependent operation (e.g. analog I/O) not supported by the expander on that module

## Notes

- Modules are referenced by letter A-H (preferred) or by their underlying numeric channel 0-7 (TCA9548A has 8 channels)
- Pin numbers range from 0-7 (matching the AD5593R's 8 I/O pins; other supported chips may differ)
- ADC/DAC values are 12-bit (0-4095) on the AD5593R
- Voltage reference is typically 2.5V or 5V depending on configuration
- The library automatically configures pins as needed for operations
- Not every expander chip supports every operation — GPIO-only chips will raise `NotImplementedError` for analog/voltage-reference calls
