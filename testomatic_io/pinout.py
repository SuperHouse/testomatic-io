"""
Canonical GPIO pin and I2C address map for the physical Testomatic chassis
wiring. Centralised here so a wiring change touches one file instead of
magic numbers scattered across every subsystem module.

GPIO pins are gpiod line names ("GPIOnn", matching BCM numbering) rather
than Blinka board.Dnn objects -- see testomatic_io/gpio.py for why.
"""

# Power rail relays (BCM GPIO, active-high)
RAIL_3V3_RELAY_PIN = "GPIO22"
RAIL_5V_RELAY_PIN = "GPIO27"
RAIL_12V_RELAY_PIN = "GPIO17"

# Power rail sensors: INA260, I2C bus 1, NOT behind the TCA9548A mux
RAIL_3V3_SENSOR_ADDRESS = 0x42
RAIL_5V_SENSOR_ADDRESS = 0x41
RAIL_12V_SENSOR_ADDRESS = 0x40

# All IOMOD interrupts OR'd onto one pin, external pull-up, active-low
IOMOD_INTERRUPT_PIN = "GPIO16"

# External "test start" button, external pull-up, active-low
BUTTON_PIN = "GPIO20"

# Piezo beeper, active-high, on/off only (no PWM)
BEEPER_PIN = "GPIO23"

# Both EEPROMs are CAT24C32 on I2C bus 0 (the RPi's dedicated HAT ID EEPROM
# bus), not bus 1 where every other I2C device on the chassis lives.
TEST_MODULE_EEPROM_ADDRESS = 0x51
CHASSIS_EEPROM_ADDRESS = 0x50
