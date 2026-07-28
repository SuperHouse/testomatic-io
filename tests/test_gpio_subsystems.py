"""
Exercises the four fixed-GPIO subsystems (button, beeper, interrupts, power
rails) through the real gpio.py against the fake gpiod backend, to guard
the active-high/active-low inversions each one is responsible for.
"""

from gpiod.line import Value

from testomatic_io.beeper import Beeper
from testomatic_io.button import Button
from testomatic_io.interrupts import Interrupts
from testomatic_io.power.rails import PowerRails


def test_button_is_active_low(fake_gpio_lines):
    button = Button()
    button.init()

    fake_gpio_lines["GPIO20"] = Value.INACTIVE  # driven low = pressed
    assert button.pressed() is True

    fake_gpio_lines["GPIO20"] = Value.ACTIVE  # pulled high = released
    assert button.pressed() is False


def test_beeper_is_active_high(fake_gpio_lines):
    beeper = Beeper()
    beeper.init()
    assert fake_gpio_lines["GPIO23"] == Value.INACTIVE

    beeper.on()
    assert fake_gpio_lines["GPIO23"] == Value.ACTIVE

    beeper.off()
    assert fake_gpio_lines["GPIO23"] == Value.INACTIVE


def test_interrupts_is_active_low(fake_gpio_lines):
    interrupts = Interrupts()
    interrupts.init()

    fake_gpio_lines["GPIO16"] = Value.ACTIVE  # idle
    assert interrupts.is_asserted() is False

    fake_gpio_lines["GPIO16"] = Value.INACTIVE  # some module asserting
    assert interrupts.is_asserted() is True


def test_power_rails_are_active_high(fake_gpio_lines):
    rails = PowerRails()
    rails.init()

    assert rails.get_3v3() is False
    assert rails.get_5v() is False
    assert rails.get_12v() is False

    rails.set_3v3(True)
    assert rails.get_3v3() is True
    assert fake_gpio_lines["GPIO22"] == Value.ACTIVE

    rails.set_3v3(False)
    assert rails.get_3v3() is False
    assert fake_gpio_lines["GPIO22"] == Value.INACTIVE
