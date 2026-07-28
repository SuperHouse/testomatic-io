"""
Contract tests for testomatic_io.gpio's digital_output/digital_input: both
must return an object with a plain boolean `.value` get/set, regardless of
which GPIO backend sits underneath. These were used, ad hoc and uncommitted,
to verify the digitalio -> gpiod swap (see CLAUDE.md); committing them means
the same check is available for free if the backend is ever swapped again.
"""

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
