"""
Stubs the Blinka/gpiod/hardware packages testomatic_io imports at module
load time, so the whole package (and this test suite) can run on a machine
with no real Raspberry Pi -- see CLAUDE.md's hardware-stubbing note.

This runs once, before any test file imports testomatic_io: Python caches
modules in sys.modules on first import, so whichever fakes are installed
here are what every test's `import testomatic_io` gets, regardless of test
order.

Individual tests that need to control a specific dependency's behaviour
(e.g. simulating an absent I2C device) monkeypatch that one name on the
already-imported testomatic_io submodule directly, rather than re-stubbing
sys.modules -- see tests/test_eeprom.py and tests/test_power_sensors.py.
"""

import glob
import sys
import types
from enum import Enum
from unittest.mock import MagicMock

import pytest


# ---- fake gpiod (see testomatic_io/gpio.py) ----


class _FakeValue(Enum):
    INACTIVE = 0
    ACTIVE = 1


class _FakeDirection(Enum):
    AS_IS = 0
    INPUT = 1
    OUTPUT = 2


class _FakeBias(Enum):
    AS_IS = 0
    DISABLED = 1
    PULL_UP = 2
    PULL_DOWN = 3


#: Simulated GPIO line state, keyed by gpiod line name (e.g. "GPIO22").
#: Real GPIO lines are shared, stateful hardware, so the fake models that
#: the same way -- one dict behind every fake LineRequest. Cleared between
#: tests by the reset_fake_gpio_lines autouse fixture below.
FAKE_GPIO_LINES = {}

#: Line names the fake gpiochip exposes -- must match pinout.py.
_KNOWN_GPIO_LINES = {"GPIO22", "GPIO27", "GPIO17", "GPIO16", "GPIO20", "GPIO23"}


class _FakeLineSettings:
    def __init__(self, direction=_FakeDirection.AS_IS, bias=_FakeBias.AS_IS,
                 output_value=_FakeValue.INACTIVE):
        self.direction = direction
        self.bias = bias
        self.output_value = output_value


class _FakeLineRequest:
    def __init__(self, line_name, settings):
        self._line_name = line_name
        if settings.direction == _FakeDirection.OUTPUT:
            FAKE_GPIO_LINES[line_name] = settings.output_value

    def get_value(self, line_name):
        return FAKE_GPIO_LINES.get(line_name, _FakeValue.INACTIVE)

    def set_value(self, line_name, value):
        FAKE_GPIO_LINES[line_name] = value

    def release(self):
        pass


class _FakeChip:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def line_offset_from_id(self, line_name):
        if line_name not in _KNOWN_GPIO_LINES:
            raise OSError(f"no such line: {line_name}")
        return sorted(_KNOWN_GPIO_LINES).index(line_name)

    def close(self):
        pass


def _fake_request_lines(path, consumer=None, config=None):
    ((line_name, settings),) = config.items()
    return _FakeLineRequest(line_name, settings)


def _install_fake_gpiod():
    line_mod = types.ModuleType("gpiod.line")
    line_mod.Value = _FakeValue
    line_mod.Direction = _FakeDirection
    line_mod.Bias = _FakeBias

    gpiod_mod = types.ModuleType("gpiod")
    gpiod_mod.line = line_mod
    gpiod_mod.Chip = _FakeChip
    gpiod_mod.LineSettings = _FakeLineSettings
    gpiod_mod.request_lines = _fake_request_lines
    gpiod_mod.is_gpiochip_device = lambda path: True

    sys.modules["gpiod"] = gpiod_mod
    sys.modules["gpiod.line"] = line_mod


# ---- fake Blinka (board/busio/adafruit_tca9548a) ----


def _install_fake_blinka():
    board_mod = types.ModuleType("board")
    board_mod.D1 = "D1"
    board_mod.D0 = "D0"
    board_mod.I2C = lambda: "fake-i2c-bus1"
    sys.modules["board"] = board_mod

    busio_mod = types.ModuleType("busio")
    busio_mod.I2C = lambda scl, sda: f"fake-i2c-bus0({scl},{sda})"
    sys.modules["busio"] = busio_mod

    tca_mod = types.ModuleType("adafruit_tca9548a")
    tca_mod.TCA9548A = lambda i2c: "fake-mux"
    sys.modules["adafruit_tca9548a"] = tca_mod


# ---- fake ad5593r package ----


class _FakePinMode:
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    ADC = "ADC"
    DAC = "DAC"


class _FakeAD5593R:
    """
    Returns a fresh MagicMock per instantiation (rather than being a
    MagicMock class itself, which would hand out the same `.return_value`
    instance every call) so each AD5593RDriver in a test gets its own chip
    double, and tests can assert on exactly the calls that driver made.
    """

    def __new__(cls, *args, **kwargs):
        return MagicMock(name="AD5593R-chip")


def _install_fake_ad5593r():
    mod = types.ModuleType("ad5593r")
    mod.AD5593R = _FakeAD5593R
    mod.PinMode = _FakePinMode
    sys.modules["ad5593r"] = mod


# ---- fake mcp23008 package ----


class _FakeMCP23008PinMode:
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class _FakeMCP23008:
    """Same rationale as _FakeAD5593R: a fresh MagicMock per instantiation,
    not a MagicMock class, so each driver instance gets its own chip
    double."""

    def __new__(cls, *args, **kwargs):
        return MagicMock(name="MCP23008-chip")


def _install_fake_mcp23008():
    mod = types.ModuleType("mcp23008")
    mod.MCP23008 = _FakeMCP23008
    mod.PinMode = _FakeMCP23008PinMode
    sys.modules["mcp23008"] = mod


# ---- fake CircuitPython fixed-address device packages ----
# Minimal placeholders so `import testomatic_io` succeeds; tests that need
# specific present/absent or read/write behaviour monkeypatch the INA260/
# EEPROM_I2C attribute on the relevant testomatic_io submodule directly.


def _install_fake_circuitpython_devices():
    ina260_mod = types.ModuleType("adafruit_ina260")
    ina260_mod.INA260 = object
    sys.modules["adafruit_ina260"] = ina260_mod

    lc32_mod = types.ModuleType("adafruit_24lc32")
    lc32_mod.EEPROM_I2C = object
    sys.modules["adafruit_24lc32"] = lc32_mod


def _install_fake_gpiochip_glob():
    """
    testomatic_io/gpio.py enumerates /dev/gpiochip* via glob.glob() to find
    which chip exposes a given line name -- there are no such device files
    on a dev machine, so make that one pattern resolve to a single fake
    chip. Patches the real glob module process-wide (rather than pytest's
    monkeypatch fixture) since this needs to be in place before the first
    test imports testomatic_io.gpio, for the whole session.
    """
    real_glob = glob.glob

    def fake_glob(pattern, *args, **kwargs):
        if pattern == "/dev/gpiochip*":
            return ["/dev/gpiochip0"]
        return real_glob(pattern, *args, **kwargs)

    glob.glob = fake_glob


_install_fake_gpiod()
_install_fake_gpiochip_glob()
_install_fake_blinka()
_install_fake_ad5593r()
_install_fake_mcp23008()
_install_fake_circuitpython_devices()


@pytest.fixture(autouse=True)
def reset_fake_gpio_lines():
    """Clear simulated GPIO line state between tests so e.g. a relay left
    on by one test doesn't leak into the next."""
    FAKE_GPIO_LINES.clear()
    yield
    FAKE_GPIO_LINES.clear()


@pytest.fixture
def fake_gpio_lines():
    """Direct access to the simulated GPIO line state, for tests that need
    to assert on it or drive a line externally (e.g. simulating a button
    press)."""
    return FAKE_GPIO_LINES
