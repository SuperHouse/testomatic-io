# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

IOMod is a Python library for controlling multiple I/O expander modules (ADC/DAC/GPIO chips) that sit behind a TCA9548A I2C multiplexer, typically on a Raspberry Pi. Each of the mux's 8 channels can carry a module with a different expander chip; the library identifies which chip is on each channel automatically and dispatches to the right driver, so callers never need to say what type of module they're talking to.

## Commands

There is no test suite, linter, or CI configured yet.

```bash
# Editable install for local development (pulls in adafruit-blinka, tca9548a driver, etc.)
pip install -e .

# Or from requirements.txt directly
pip install -r requirements.txt

# Run the example script against real hardware
python examples/iomod_example.py
python examples/iomod_example.py interactive
```

`import iomod` requires actual Raspberry Pi (or other Blinka-supported) hardware — `board`/Adafruit-Blinka does platform detection at import time and raises `NotImplementedError` on unsupported platforms (e.g. a Mac dev machine). When working on this repo without hardware, verify driver logic by stubbing `sys.modules['board']` and `sys.modules['adafruit_tca9548a']` with fakes before importing `iomod`, rather than trying to run it directly.

## Architecture

### Module addressing

Modules are referenced by letter (`'A'`-`'H'`, preferred) or by numeric TCA9548A channel (`0`-`7`); `iomod/iomod.py`'s `_module_index`/`_module_letter` convert between the two, and `IOMod._validate_module_id` normalizes any call's `module_id` to the numeric form before use. `scan_modules()` returns letters.

### Driver abstraction (the core design)

Expander chip support is pluggable so new chip types can be added without touching `IOMod`:

- `iomod/drivers/base.py` — `ExpanderDriver`, the interface every chip driver implements: `pin_mode`, `digital_write`/`digital_read`, `toggle`, `analog_read`/`analog_write`, `read_voltage`, `set_vref`/`get_vref`, `set_dac_range`/`get_dac_range`, `set_ldac_mode`, `reset`, plus a `probe(i2c_adapter, address)` classmethod used for auto-detection. Operations a chip doesn't support are left unimplemented and raise `NotImplementedError` via the base class.
- `iomod/drivers/__init__.py` — `DRIVERS`, the ordered list of registered driver classes, and `identify_driver(i2c_adapter, addresses)`, which checks each I2C address found on a module's channel against each driver's `probe()`.
- `iomod/drivers/ad5593r.py` — `AD5593RDriver`, the reference implementation, at I2C address `0x10`.
- `iomod/iomod.py`'s `IOMod._get_module()` scans a module's channel (`ChannelI2CAdapter.scan()`), calls `identify_driver()`, and instantiates whichever driver matches — no chip type is ever hardcoded. `scan_modules()` does the same per channel to report which modules are populated.

To add a new chip (e.g. MCP23008, Serial Wombat): write a driver module implementing the subset of `ExpanderDriver` that chip supports, and add its class to `DRIVERS` in `iomod/drivers/__init__.py`. See `README.md`'s "Adding a New Expander Driver" section.

### The AD5593R driver does NOT use the published `ad5593r` PyPI package

This is the single most important non-obvious fact in this codebase. `ad5593r>=0.1.1` is still declared in `pyproject.toml`/`requirements.txt`, but it is **not imported anywhere**. The published package's `AD5593R` class opens its own `smbus2.SMBus(bus_number)` connection scoped to a Linux I2C bus number and has no way to accept an external transport — so it cannot be routed through the TCA9548A multiplexer's per-channel addressing, which is the whole point of this library. Its method names (`write1`, `set_output_mode`, `write_dac`, etc.) also don't match what `IOMod` calls.

Instead, `iomod/drivers/ad5593r.py` implements the AD5593R register-level protocol in-house against the generic `i2c_adapter` interface (`writeto`/`readfrom`/`scan`), ported from `old/ad5593r/ad5593r_library.py` — an earlier, mux-compatible version of this same driver. The `ad5593r` dependency is kept declared (with a comment explaining why) pending a possible future upstream release of that package that accepts an injectable transport.

### I2C adapter layer

`ChannelI2CAdapter` in `iomod/iomod.py` wraps a CircuitPython `adafruit_tca9548a` channel object (which exposes `readfrom_into`/`writeto`) to provide the plain `readfrom`/`writeto`/`scan` interface that drivers expect, acquiring/releasing the channel's I2C lock around each call.

### Shared constants

`iomod/constants.py` holds `HIGH`/`LOW`/`INPUT`/`OUTPUT`/`ADC`/`DAC`. These live outside `iomod/iomod.py` specifically so that `iomod/drivers/*` can import them without a circular import (`iomod.py` imports from `drivers`, so `drivers` can't import back from `iomod.py`). `iomod/iomod.py` re-imports and re-exports them for backward-compatible access as `iomod.HIGH`, etc.

### `old/` directory

`old/ad5593r/` contains earlier, untracked (gitignored) working files, including the pre-refactor `ad5593r_library.py` that the current `AD5593RDriver` was ported from, and `DIAGNOSIS.md` documenting an unresolved DAC range bug (`setDACRange`/`getDACRange` debug prints in `iomod/drivers/ad5593r.py` are intentionally left in from that investigation — don't strip them as cleanup). This directory is not part of the installable package.
