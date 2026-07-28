"""
Low-level hardware setup helpers shared across subsystems: gpiod line setup
for the GPIO-based subsystems (power rail relays, button, beeper, IOMOD
interrupt line), and opening I2C bus 0 (used by both Chassis's identity
EEPROM and TestModule's identity EEPROM).

GPIO uses gpiod (the modern Linux GPIO character-device API) rather than
Blinka's digitalio, deliberately -- digitalio's Raspberry Pi backend needs
RPi.GPIO on Pi 4 and earlier but the separate `lgpio` package on Pi 5 (see
https://github.com/adafruit/Adafruit_Blinka/pull/911), which Blinka can't
auto-install via pip because there's no environment marker that
distinguishes a Pi 5 from other aarch64/armv7l boards -- see issue #5.
gpiod talks to /dev/gpiochipN directly and needs no board-specific backend
at all, so it works identically across Pi 3/4/5 with a single dependency.
I2C (`busio`/`board.I2C()`) is unaffected and stays on Blinka -- that code
path never touches RPi.GPIO/lgpio in the first place.
"""

import glob

import board
import busio
import gpiod
from gpiod.line import Bias, Direction, Value

_CONSUMER = "testomatic-io"


def _find_chip_path(line_name):
    """
    Find the /dev/gpiochipN device that exposes a line named `line_name`.
    Needed because the chip enumeration is board-dependent -- e.g. the
    header GPIOs are gpiochip0 on Pi 4 but a higher-numbered chip on Pi 5's
    RP1 southbridge -- while the "GPIOnn" line names (matching the BCM
    numbering used throughout pinout.py) are stable across both, per the
    Raspberry Pi kernel's gpio-line-names devicetree convention. Confirmed
    against libgpiod's Python API docs, not yet against real hardware.
    """
    for path in sorted(glob.glob("/dev/gpiochip*")):
        with gpiod.Chip(path) as chip:
            try:
                chip.line_offset_from_id(line_name)
                return path
            except (OSError, ValueError):
                continue
    raise RuntimeError(f"no gpiochip exposes a line named {line_name!r}")


class _Pin:
    """
    Adapts a single-line gpiod.LineRequest to the plain `.value` boolean
    property the rest of the codebase expects, so swapping the underlying
    GPIO backend doesn't ripple into button.py/beeper.py/interrupts.py/
    power/rails.py.
    """

    def __init__(self, request, line_name):
        self._request = request
        self._line_name = line_name

    @property
    def value(self):
        return self._request.get_value(self._line_name) == Value.ACTIVE

    @value.setter
    def value(self, new_value):
        self._request.set_value(
            self._line_name, Value.ACTIVE if new_value else Value.INACTIVE
        )


def digital_output(pin, initial_value=False):
    """Configure `pin` (a gpiod line name, e.g. "GPIO22") as a digital output"""
    path = _find_chip_path(pin)
    settings = gpiod.LineSettings(
        direction=Direction.OUTPUT,
        output_value=Value.ACTIVE if initial_value else Value.INACTIVE,
    )
    request = gpiod.request_lines(path, consumer=_CONSUMER, config={pin: settings})
    return _Pin(request, pin)


def digital_input(pin, pull=None):
    """
    Configure `pin` (a gpiod line name, e.g. "GPIO22") as a digital input.
    `pull` is an optional gpiod.line.Bias value (e.g. Bias.PULL_UP); leave
    as None for lines with an external pull resistor.
    """
    path = _find_chip_path(pin)
    settings = gpiod.LineSettings(direction=Direction.INPUT, bias=pull or Bias.AS_IS)
    request = gpiod.request_lines(path, consumer=_CONSUMER, config={pin: settings})
    return _Pin(request, pin)


def open_i2c_bus0():
    """
    Open I2C bus 0 -- the Raspberry Pi's dedicated HAT ID EEPROM bus, distinct
    from board.I2C() (bus 1) used by everything else on the chassis. Blinka
    has no board.SCL0/SDA0 on Raspberry Pi; bus 0 is GPIO1/GPIO0 (the
    ID_SC/ID_SD pins), which Blinka exposes as board.D1/board.D0 -- see
    i2cPorts in adafruit_blinka.microcontroller.bcm2712.pin. Other
    Blinka-supported boards that do define board.SCL0/SDA0 (e.g. Pico/FTDI/
    Radxa boards) use those instead, rather than hardcoding to the
    Raspberry-Pi-specific alias -- see issue #6.
    """
    scl = getattr(board, "SCL0", board.D1)
    sda = getattr(board, "SDA0", board.D0)
    return busio.I2C(scl, sda)
