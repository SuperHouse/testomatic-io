# IOMod Library

A Python wrapper library for controlling multiple IOMOD I/O Expander Modules through a TCA9548A I2C multiplexer.

## Overview

The IOMod library provides a high-level interface for managing multiple ADC/DAC/GPIO modules connected through a TCA9548A I2C multiplexer. It allows you to easily select specific modules and perform digital and analog operations on them.

## Features

- **Module Selection**: Automatically manages TCA9548A multiplexer channels
- **Digital I/O**: Read and write digital values to GPIO pins
- **Analog I/O**: Read ADC values and write DAC values
- **Pin Configuration**: Configure pins as INPUT, OUTPUT, ADC, or DAC
- **Voltage Reference Management**: Enable/disable and read reference voltage
- **Error Handling**: Comprehensive validation and error reporting
- **Module Scanning**: Automatically detect available modules

## Hardware Requirements

- TCA9548A I2C multiplexer
- One or more IOMOD modules (connected via I2C)
- Compatible I2C bus (e.g., Raspberry Pi I2C)

## Dependencies

```bash
pip install adafruit-circuitpython-tca9548a
pip install adafruit-circuitpython-board
```

## Quick Start

```python
import iomod_library as iomod

# Initialize the system
iomod.init()

# Scan for available modules
modules = iomod.scan_modules()
print(f"Available modules: {modules}")

# Write HIGH to pin 4 on module 3
iomod.digitalwrite(3, 4, iomod.HIGH)

# Read from pin 1 on module 2
value = iomod.digitalread(2, 1)

# Read analog voltage from pin 3 on module 1
voltage = iomod.readvoltage(1, 3)
```

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
Scan for available modules and return a list of working module IDs (0-7).

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

## Examples

### Basic Digital I/O

```python
import iomod_library as iomod

# Initialize
iomod.init()

# Configure pin 2 as output on module 0
iomod.pinmode(0, 2, iomod.OUTPUT)

# Write HIGH
iomod.digitalwrite(0, 2, iomod.HIGH)

# Configure pin 1 as input on module 0
iomod.pinmode(0, 1, iomod.INPUT)

# Read value
value = iomod.digitalread(0, 1)
print(f"Pin 1 reads: {'HIGH' if value else 'LOW'}")
```

### Analog Operations

```python
import iomod_library as iomod

# Initialize
iomod.init()

# Enable voltage reference
iomod.setvref(0, True)

# Configure pin 3 as ADC
iomod.pinmode(0, 3, iomod.ADC)

# Read voltage
voltage = iomod.readvoltage(0, 3)
print(f"Voltage: {voltage:.3f}V")

# Configure pin 4 as DAC
iomod.pinmode(0, 4, iomod.DAC)

# Write analog value (50% of full scale)
iomod.analogwrite(0, 4, 2048)
```

### Multiple Modules

```python
import iomod_library as iomod

# Initialize
iomod.init()

# Scan for modules
modules = iomod.scan_modules()

# Control multiple modules
for module_id in modules:
    # Set pin 0 as output
    iomod.pinmode(module_id, 0, iomod.OUTPUT)
    
    # Write different states
    state = module_id % 2  # Alternate HIGH/LOW
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

- **Invalid module ID**: Must be 0-7
- **Invalid pin number**: Must be 0-7  
- **Invalid pin mode**: Must be INPUT, OUTPUT, ADC, or DAC
- **Module not found**: Module not responding on I2C bus
- **I2C errors**: Communication failures

## Notes

- Module IDs range from 0-7 (TCA9548A has 8 channels)
- Pin numbers range from 0-7 (AD5593R has 8 I/O pins)
- ADC values are 12-bit (0-4095)
- DAC values are 12-bit (0-4095)
- Voltage reference is typically 2.5V or 5V depending on configuration
- The library automatically configures pins as needed for operations
