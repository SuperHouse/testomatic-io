"""
AD5593R driver

Talks to the AD5593R ADC/DAC/GPIO expander over a generic i2c_adapter
exposing writeto()/readfrom()/scan(), such as ChannelI2CAdapter. This is a
from-scratch implementation rather than a wrapper around the published
"ad5593r" PyPI package: that package opens its own smbus2 connection scoped
to a Linux bus number and has no way to accept an external transport, so it
cannot be routed through the TCA9548A multiplexer's channel selection. The
register-level protocol here is the same one this project used before the
multi-driver refactor (see old/ad5593r/ad5593r_library.py), adapted to the
ExpanderDriver interface.

Original by Tristan Muller for MicroPython (https://101robotics.com).
Modified for Python 3 and DAC output support by Jonathan Oxer.
"""

import time  # For delays after reset

from ..constants import INPUT, OUTPUT, ADC, DAC
from .base import ExpanderDriver

### Keywords :
AD5593R_ALL = 0
AD5593R_ADC = 1
AD5593R_DAC = 2
AD5593R_OUTPUT = 3
AD5593R_INPUT  = 4

### Error codes
AD5593R_LDAC_ERROR    = 0xFF83

##### POINTER BYTE CONSTANTS :
### Mode bits :
AD5593R_CONFIG_MODE   = 0b0000 << 4
AD5593R_DAC_WRITE     = 0b0001 << 4
AD5593R_ADC_READBACK  = 0b0100 << 4
AD5593R_DAC_READBACK  = 0b0101 << 4
AD5593R_GPIO_READBACK = 0b0110 << 4
AD5593R_REG_READBACK  = 0b0111 << 4

### LDAC MODE
AD5593R_LDAC_DIRECT   = 0        # COPY input register direct to DAC. (default)
AD5593R_LDAC_HOLD     = 1        # HOLD in input registers
AD5593R_LDAC_RELEASE  = 2        # RELEASE all input registers to DAC simultaneously

### Control Register : (Descriptions from the datasheet)
AD5593R_NOP            = 0b0000  # No operation
AD5593R_ADC_SEQ_REG    = 0b0010  # Selects ADC for conversion (1 byte blank and 1 for the 8 I/Os)
AD5593R_GP_CONTR_REF   = 0b0011  # DAC and ADC control register
AD5593R_ADC_PIN_CONF   = 0b0100  # Selects which pins are ADC inputs
AD5593R_DAC_PIN_CONF   = 0b0101  # Selects which pins are DAC outputs
AD5593R_PULLDOWN_CONF  = 0b0110  # Selects which pins have an 85kOhms pull-down resistor to GND
AD5593R_LDAC_MODE      = 0b0111  # Selects the operation of the load DAC
AD5593R_GPIO_W_CONF    = 0b1000  # Selects which pins are general-purpose outputs
AD5593R_GPIO_W_DATA    = 0b1001  # Writes data to general-purpose outputs
AD5593R_GPIO_R_CONF    = 0b1010  # Selects which pins are general-purpose inputs
AD5593R_PWRDWN_REFCONF = 0b1011  # Powers down the DACs and enables/disables the reference
AD5593R_OPENDRAIN_CONF = 0b1100  # Selects open-drain or push-pull for general-purpose outputs
AD5593R_3_STATES_PINS  = 0b1101  # Selects which pins are three-stated
AD5593R_SOFT_RESET     = 0b1111  # Resets the AD5593R
AD5593R_BLANK          = 0b00000000

#: I2C address the AD5593R responds at on IOMOD hardware
DEFAULT_ADDRESS = 0x10


class _AD5593RChip:
    """Register-level AD5593R protocol implementation"""

    def __init__(self, i2c, address=DEFAULT_ADDRESS, advance=0):
        self._i2c = i2c
        self._address = address
        self._data = bytearray(3)
        self._advance = advance

        # Check if device is present on the I2C bus
        devices = self._i2c.scan() if hasattr(self._i2c, 'scan') else []
        if isinstance(devices, list) and address not in devices:
            raise OSError('AD5593R not found at I2C address {:#x}'.format(address))

    def INPUT(self, pin):
        pin = self.validate_pin(pin)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_GPIO_R_CONF, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GPIO_R_CONF
        self._data[1] = reg[0]
        self._data[2] = reg[1] | (1 << pin)
        self._write()

    def OUTPUT(self, pin):
        pin = self.validate_pin(pin)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_GPIO_W_CONF, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GPIO_W_CONF
        self._data[1] = reg[0]
        self._data[2] = reg[1] | (1 << pin)
        self._write()

    def ADC(self, pin, range=1):
        pin = self.validate_pin(pin)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_ADC_PIN_CONF, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_ADC_PIN_CONF
        self._data[1] = reg[0]
        self._data[2] = reg[1] | (1 << pin)
        self._write()

        if self._advance == 0:
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] | (1 << 1)  # Activate Vref
            self._data[2] = reg[1]
            self._write()

            if range == 2:
                reg = self._read(AD5593R_REG_READBACK | AD5593R_GP_CONTR_REF, 2)
                self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GP_CONTR_REF
                self._data[1] = reg[0]
                self._data[2] = reg[1] | (1 << 5)  # Range 2x Vref
                self._write()
            else:
                reg = self._read(AD5593R_REG_READBACK | AD5593R_GP_CONTR_REF, 2)
                self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GP_CONTR_REF
                self._data[1] = reg[0]
                self._data[2] = reg[1] & ~(1 << 5)  # Range Vref
                self._write()

    def DAC(self, pin, range=2):
        """
        Configure a pin as a DAC output

        Args:
            pin (int): The pin to configure as DAC output (0-7)
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref)
        """
        pin = self.validate_pin(pin)

        # NOW configure the pin as DAC after range is set
        reg = self._read(AD5593R_REG_READBACK | AD5593R_DAC_PIN_CONF, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_DAC_PIN_CONF
        self._data[1] = reg[0]
        self._data[2] = reg[1] | (1 << pin)
        self._write()
        print(f"DEBUG: DAC() configured pin {pin} as DAC output")

        # IMPORTANT: Set the range BEFORE configuring the pin as DAC
        # This ensures the range is established before the DAC is enabled
        if self._advance == 0:
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] | (1 << 1)  # Activate Vref
            self._data[2] = reg[1]
            self._write()

            if range == 2:
                reg = self._read(AD5593R_REG_READBACK | AD5593R_GP_CONTR_REF, 2)
                self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GP_CONTR_REF
                self._data[1] = reg[0]
                self._data[2] = reg[1] | (1 << 5)  # Range 2x Vref
                self._write()
                print(f"DEBUG: DAC() set range=2x")
            else:
                reg = self._read(AD5593R_REG_READBACK | AD5593R_GP_CONTR_REF, 2)
                self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GP_CONTR_REF
                self._data[1] = reg[0]
                self._data[2] = reg[1] & ~(1 << 5)  # Range Vref
                self._write()
                print(f"DEBUG: DAC() set range=1x")

    def digitalRead(self, pin):
        """
        Read the digital state of a GPIO pin configured as input

        Args:
            pin (int): The pin to read (0-7)

        Returns:
            int: 1 if the pin is high, 0 if the pin is low
        """
        pin = self.validate_pin(pin)

        # Ensure the pin is configured as a GPIO input
        reg = self._read(AD5593R_REG_READBACK | AD5593R_GPIO_R_CONF, 2)
        if not (reg[1] & (1 << pin)):
            # If not already configured as input, configure it
            self.INPUT(pin)

        # Read the GPIO input data
        self._i2c.writeto(self._address, bytes([AD5593R_GPIO_READBACK]))
        data = self._i2c.readfrom(self._address, 2)

        # Check if the pin bit is set
        return 1 if (data[1] & (1 << pin)) else 0

    def getVref(self):
        """
        Get the voltage reference value.
        Note: AD5593R uses an internal 2.5V reference.
        This function returns the actual reference voltage (2.5V).
        """
        # Return the actual internal reference voltage of 2.5V
        # Note: The DAC can operate in 1x or 2x Vref mode,
        # but the actual Vref is always 2.5V
        return 2.5

    def getDACRange(self):
        """
        Get the current DAC range setting.

        Returns:
            int: DAC range (1 = 1x Vref, 2 = 2x Vref)
        """
        mask = 0b00100000
        # Check GP_CONTR_REF register (this is what DAC() function uses)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_GP_CONTR_REF, 2)
        print(f"DEBUG: GP_CONTR_REF read: reg[0]={reg[0]:02x} ({reg[0]:08b}), reg[1]={reg[1]:02x} ({reg[1]:08b})")
        # Range bit is in reg[1], bit 5
        if reg[1] & mask:
            print(f"DEBUG: Range bit is SET in reg[1] (reg[1]={reg[1]:02x} & {mask:02x} = {reg[1] & mask:02x})")
            return 2  # 2x Vref mode
        else:
            print(f"DEBUG: Range bit is CLEAR in reg[1] (reg[1]={reg[1]:02x} & {mask:02x} = {reg[1] & mask:02x})")
            return 1  # 1x Vref mode

    def setDACRange(self, range=2):
        """
        Set the DAC range for all DAC pins

        Args:
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref)
        """
        if self._advance == 0:
            # First ensure Vref is activated
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            print(f"DEBUG: PWRDWN_REFCONF before: reg[0]={reg[0]:02x} ({reg[0]:08b}), reg[1]={reg[1]:02x} ({reg[1]:08b})")
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] | (1 << 1)  # Activate Vref (bit 1)
            self._data[2] = reg[1]
            print(f"DEBUG: Writing to PWRDWN_REFCONF: byte1={self._data[1]:02x} (activating Vref bit)")
            self._write()
            # Read back to verify
            reg2 = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            print(f"DEBUG: PWRDWN_REFCONF after: reg[0]={reg2[0]:02x} ({reg2[0]:08b}), reg[1]={reg2[1]:02x} ({reg2[1]:08b})")

            # Note: The DAC range is now handled by calling DAC() function
            # which properly sets GP_CONTR_REF register.
            # This function is kept for backward compatibility but doesn't actually
            # set a separate range - it relies on DAC() to do it.
            print(f"DEBUG: setDACRange(range={range}) called - will be applied when DAC() is called")

    def setVref(self, activate):
        if activate:
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] | (1 << 1)  # Activate Vref
            self._data[2] = reg[1]
            self._write()
        else:
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] & ~(1 << 1)  # Deactivate Vref
            self._data[2] = reg[1]
            self._write()

    # Latch DAC must be called AFTER setVref
    def setLDACMode(self, ldac_mode):
        if (ldac_mode > AD5593R_LDAC_RELEASE):
            return AD5593R_LDAC_ERROR
        self._data[0] = AD5593R_LDAC_MODE
        self._data[1] = AD5593R_BLANK
        self._data[2] = ldac_mode
        self._write()

    def readVoltage(self, pin, average=3):
        pin = self.validate_pin(pin)
        vref = self.getVref()
        value = self.analogRead(pin, average)
        return (value / 4096) * vref

    def digitalWrite(self, pin, value=0):
        pin = self.validate_pin(pin)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_GPIO_W_DATA, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GPIO_W_DATA
        self._data[1] = AD5593R_BLANK
        if value:
            self._data[2] = reg[1] | (1 << pin)  # 1
        else:
            self._data[2] = reg[1] & ~(1 << pin)  # 0
        self._write()

    def analogRead(self, pin, average=1):
        pin = self.validate_pin(pin)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_ADC_SEQ_REG, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_ADC_SEQ_REG
        self._data[1] = reg[0] | (1 << 1)  # Activate repetition
        self._data[2] = (1 << pin)
        self._write()

        # Python 3 compatible change for I2C read
        self._i2c.writeto(self._address, bytes([AD5593R_ADC_READBACK]))
        values = [0] * average
        for x in range(average):
            msg = self._i2c.readfrom(self._address, 2)
            values[x] = ((msg[0] & 0x0F) << 8) + msg[1]
        return int(sum(values) / len(values))

    def analogWrite(self, pin, value, range=2):
        """
        Write an analog value to a DAC pin

        Args:
            pin (int): The DAC pin to write to (0-7)
            value (int): The analog value to write (0-4095 for 12-bit DAC)
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref, default: 2)
        """
        pin = self.validate_pin(pin)

        print(f"DEBUG: analogWrite called with range={range}")

        # Clamp value to 12-bit range (0-4095)
        value = max(0, min(4095, int(value)))

        # Split 12-bit value into high and low bytes
        # High byte contains the 4 MSBs, low byte contains the 8 LSBs
        high_byte = (value >> 8) & 0x0F  # Only 4 bits for high byte
        low_byte = value & 0xFF          # 8 bits for low byte

        # Write DAC value using AD5593R_DAC_WRITE mode
        self._data[0] = AD5593R_DAC_WRITE | pin  # Pin selection in lower 4 bits
        self._data[1] = high_byte
        self._data[2] = low_byte
        self._write()

    def toggle(self, pin):
        pin = self.validate_pin(pin)
        reg = self._read(AD5593R_REG_READBACK | AD5593R_GPIO_W_DATA, 2)
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_GPIO_W_DATA
        self._data[1] = AD5593R_BLANK
        self._data[2] = reg[1] ^ (1 << pin)
        self._write()

    def powerAll(self, state):
        if state:  # Powering up
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] & ~(1 << 2)  # Activate Vref
            self._data[2] = reg[1]
            self._write()
        else:  # Powering down
            reg = self._read(AD5593R_REG_READBACK | AD5593R_PWRDWN_REFCONF, 2)
            self._data[0] = AD5593R_CONFIG_MODE | AD5593R_PWRDWN_REFCONF
            self._data[1] = reg[0] | (1 << 2)
            self._data[2] = reg[1]
            self._write()

    def reset(self):
        self._data[0] = AD5593R_CONFIG_MODE | AD5593R_SOFT_RESET
        self._data[1] = 0x0D
        self._data[2] = 0xAC
        self._write()
        # Wait for device to recover from reset
        time.sleep(0.1)  # 100ms delay as per datasheet recommendation

    def validate_pin(self, pin):
        # pin valid range 0..7
        if not 0 <= pin <= 7:
            raise ValueError('Invalid pin {}. Use 0-7.'.format(pin))
        return pin

    def readRegister(self, reg):
        return bin(int.from_bytes(self._read(reg, 2), byteorder='big'))

    def writeRegister(self, reg, msb, lsb):
        self._data[0] = reg
        self._data[1] = msb
        self._data[2] = lsb
        self._write()

    def readValues(self):
        return self._i2c.readfrom(self._address, 2)

    def _read(self, reg=AD5593R_BLANK, nbBytes=2):
        # Python 3 compatible change for I2C write
        self._i2c.writeto(self._address, bytes([reg]))
        return self._i2c.readfrom(self._address, nbBytes)

    def _write(self):
        # Make sure data is sent as bytes
        self._i2c.writeto(self._address, bytes(self._data))


class AD5593RDriver(ExpanderDriver):
    """ExpanderDriver adapter around the AD5593R register-level protocol"""

    NAME = "AD5593R"
    ADDRESSES = (DEFAULT_ADDRESS,)

    @classmethod
    def probe(cls, i2c_adapter, address):
        return address in cls.ADDRESSES

    def __init__(self, i2c_adapter, address=DEFAULT_ADDRESS):
        self._chip = _AD5593RChip(i2c_adapter, address=address)

    def pin_mode(self, pin, mode):
        if mode == INPUT:
            self._chip.INPUT(pin)
        elif mode == OUTPUT:
            self._chip.OUTPUT(pin)
        elif mode == ADC:
            self._chip.ADC(pin)
        elif mode == DAC:
            self._chip.DAC(pin)
        else:
            raise ValueError(f"Invalid pin mode {mode}. Use INPUT, OUTPUT, ADC, or DAC.")

    def digital_write(self, pin, value):
        self._chip.OUTPUT(pin)
        self._chip.digitalWrite(pin, value)

    def digital_read(self, pin):
        self._chip.INPUT(pin)
        return self._chip.digitalRead(pin)

    def toggle(self, pin):
        self._chip.OUTPUT(pin)
        self._chip.toggle(pin)

    def analog_read(self, pin, average=1):
        self._chip.ADC(pin)
        return self._chip.analogRead(pin, average)

    def analog_write(self, pin, value):
        self._chip.analogWrite(pin, value)

    def read_voltage(self, pin, average=1):
        self._chip.ADC(pin)
        return self._chip.readVoltage(pin, average)

    def set_vref(self, activate):
        self._chip.setVref(activate)

    def get_vref(self):
        return self._chip.getVref()

    def get_dac_range(self):
        return self._chip.getDACRange()

    def set_dac_range(self, range):
        self._chip.setDACRange(range)

    def set_ldac_mode(self, mode):
        self._chip.setLDACMode(mode)

    def reset(self):
        self._chip.reset()
