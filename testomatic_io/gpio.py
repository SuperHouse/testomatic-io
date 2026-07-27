"""
Low-level hardware setup helpers shared across subsystems: digitalio pin
setup for the GPIO-based subsystems (power rail relays, button, beeper,
IOMOD interrupt line), and opening I2C bus 0 (used by both Chassis's
identity EEPROM and TestModule's identity EEPROM).
"""

import board
import busio
import digitalio


def digital_output(pin, initial_value=False):
    """Configure `pin` as a digital output, returning the DigitalInOut"""
    dio = digitalio.DigitalInOut(pin)
    dio.direction = digitalio.Direction.OUTPUT
    dio.value = initial_value
    return dio


def digital_input(pin, pull=None):
    """Configure `pin` as a digital input, returning the DigitalInOut"""
    dio = digitalio.DigitalInOut(pin)
    dio.direction = digitalio.Direction.INPUT
    if pull is not None:
        dio.pull = pull
    return dio


def open_i2c_bus0():
    """
    Open I2C bus 0 -- the Raspberry Pi's dedicated HAT ID EEPROM bus, distinct
    from board.I2C() (bus 1) used by everything else on the chassis. Exact
    pin names depend on the Blinka board definition for this hardware and
    haven't yet been confirmed against a real Pi -- see the project
    restructure plan's "Open items" note.
    """
    return busio.I2C(board.SCL0, board.SDA0)
