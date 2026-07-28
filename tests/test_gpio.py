"""
Contract tests for testomatic_io.gpio's digital_output/digital_input: both
must return an object with a plain boolean `.value` get/set, regardless of
which GPIO backend sits underneath. These were used, ad hoc and uncommitted,
to verify the digitalio -> gpiod swap (see CLAUDE.md); committing them means
the same check is available for free if the backend is ever swapped again.
"""

import board
import pytest
from gpiod.line import Value

from testomatic_io import gpio


def test_digital_output_defaults_to_false():
    pin = gpio.digital_output("GPIO22")
    assert pin.value is False


def test_digital_output_reflects_initial_value():
    pin = gpio.digital_output("GPIO22", initial_value=True)
    assert pin.value is True


def test_digital_output_set_and_get_round_trip():
    pin = gpio.digital_output("GPIO22", initial_value=False)

    pin.value = True
    assert pin.value is True

    pin.value = False
    assert pin.value is False


def test_digital_input_reads_externally_driven_value(fake_gpio_lines):
    pin = gpio.digital_input("GPIO20")

    fake_gpio_lines["GPIO20"] = Value.ACTIVE
    assert pin.value is True

    fake_gpio_lines["GPIO20"] = Value.INACTIVE
    assert pin.value is False


def test_unknown_line_name_raises():
    with pytest.raises(RuntimeError):
        gpio.digital_output("GPIO99")


def test_open_i2c_bus0_falls_back_to_d1_d0_on_pi(monkeypatch):
    """The fake `board` module has no SCL0/SDA0, matching real Raspberry Pi
    Blinka boards -- see issue #6."""
    monkeypatch.delattr(board, "SCL0", raising=False)
    monkeypatch.delattr(board, "SDA0", raising=False)

    bus0 = gpio.open_i2c_bus0()

    assert bus0 == "fake-i2c-bus0(D1,D0)"


def test_open_i2c_bus0_prefers_scl0_sda0_when_defined(monkeypatch):
    """Boards that do define board.SCL0/SDA0 (e.g. Pico/FTDI/Radxa) should
    use those rather than the Raspberry-Pi-specific D1/D0 alias."""
    monkeypatch.setattr(board, "SCL0", "SCL0", raising=False)
    monkeypatch.setattr(board, "SDA0", "SDA0", raising=False)

    bus0 = gpio.open_i2c_bus0()

    assert bus0 == "fake-i2c-bus0(SCL0,SDA0)"
