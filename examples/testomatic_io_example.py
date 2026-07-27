#!/usr/bin/env python3
"""
testomatic-io Example Usage

Demonstrates the Testomatic chassis hardware abstraction layer: IOMODs
through the TCA9548A multiplexer, power rail control/sensing, the button,
the beeper, and the chassis/Test Module identity EEPROMs.

Hardware setup:
- TCA9548A I2C multiplexer connected to I2C bus 1
- Multiple AD5593R modules connected to different channels of the multiplexer
- Each AD5593R should be configured with address 0x10
- See testomatic_io/pinout.py for the rest of the chassis wiring
"""

import time

from testomatic_io import Chassis, TestModule, HIGH, LOW, OUTPUT
from testomatic_io.gpio import open_i2c_bus0

def main():
    """Main example function"""
    print("testomatic-io Example")
    print("======================")

    try:
        print("Initializing Chassis and Test Module...")
        # Chassis and TestModule both use I2C bus 0 for their identity
        # EEPROMs; open it once here and share it between them.
        i2c_bus0 = open_i2c_bus0()

        chassis = Chassis()
        chassis.init(i2c_bus0=i2c_bus0)

        test_module = TestModule()
        test_module.init(i2c_bus0=i2c_bus0)

        # --- IOMOD example ---
        print("\nScanning for available IOMODs...")
        available_modules = chassis.iomod.scan_modules()

        if not available_modules:
            print("No IOMODs found! Check your hardware connections.")
        else:
            print(f"Found {len(available_modules)} available modules: {available_modules}")
            module_id = available_modules[0]
            print(f"\nUsing module {module_id} for demonstration")

            print("\n--- Digital I/O Example ---")
            print("Configuring pin 2 as digital output...")
            chassis.iomod.pin_mode(module_id, 2, OUTPUT)

            print("Toggling pin 2 five times...")
            for i in range(5):
                chassis.iomod.digital_write(module_id, 2, HIGH)
                print(f"  Iteration {i+1}: Pin 2 = HIGH")
                time.sleep(0.5)

                chassis.iomod.digital_write(module_id, 2, LOW)
                print(f"  Iteration {i+1}: Pin 2 = LOW")
                time.sleep(0.5)

            print("\n--- Analog Operations Example ---")
            print("Enabling voltage reference...")
            chassis.iomod.set_vref(module_id, True)
            vref = chassis.iomod.get_vref(module_id)
            print(f"Reference voltage: {vref:.2f}V")

        # --- Power rails example ---
        print("\n--- Power Rails Example ---")
        print("Turning on 3.3V rail...")
        chassis.power.rail_3v3(True)
        time.sleep(0.2)
        reading = chassis.power.read_3v3()
        print(f"3.3V rail: {reading.voltage:.3f}V, {reading.current:.1f}mA, {reading.power:.0f}mW")
        chassis.power.rail_3v3(False)
        print("3.3V rail turned off")

        # --- Button and beeper example ---
        print("\n--- Button and Beeper Example ---")
        print(f"Button pressed: {chassis.button.pressed()}")
        print("Beeping for 0.1s...")
        chassis.beeper.beep(0.1)

        # --- EEPROM example ---
        print("\n--- EEPROM Example ---")
        chassis_id = chassis.hat_eeprom.read(0, 16)
        test_module_id = test_module.eeprom.read(0, 16)
        print(f"Chassis identity EEPROM (first 16 bytes): {chassis_id}")
        print(f"Test Module identity EEPROM (first 16 bytes): {test_module_id}")

        print("\nExample completed successfully!")

    except Exception as e:
        print(f"Error during example: {e}")
        import traceback
        traceback.print_exc()

def _parse_module(token):
    """Parse a module argument as a letter ('A'-'H', preferred) or a number (0-7)"""
    return int(token) if token.isdigit() else token

def interactive_mode():
    """Interactive mode for testing individual commands"""
    print("\nInteractive Mode")
    print("===============")
    print("Available commands (module: letter A-H, preferred, or number 0-7):")
    print("  init                    - Initialize the Chassis")
    print("  scan                    - Scan for available IOMODs")
    print("  select <module>         - Select an IOMOD")
    print("  dw <module> <pin> <val> - Digital write (val: 0 or 1)")
    print("  dr <module> <pin>       - Digital read")
    print("  aw <module> <pin> <val> - Analog write (val: 0-4095)")
    print("  ar <module> <pin>       - Analog read")
    print("  pm <module> <pin> <mode>- Pin mode (mode: 1=INPUT, 2=OUTPUT, 3=ADC, 4=DAC)")
    print("  vref <module> <on/off>  - Set voltage reference")
    print("  reset <module>          - Reset module")
    print("  toggle <module> <pin>   - Toggle digital output")
    print("  rail <3v3/5v/12v> <on/off> - Control a power rail")
    print("  power <3v3/5v/12v>      - Read a power rail's voltage/current/power")
    print("  button                  - Read the external button")
    print("  beep                    - Beep the piezo beeper")
    print("  quit                    - Exit")

    chassis = Chassis()
    rails = {"3v3": chassis.power.rail_3v3, "5v": chassis.power.rail_5v, "12v": chassis.power.rail_12v}
    readings = {"3v3": chassis.power.read_3v3, "5v": chassis.power.read_5v, "12v": chassis.power.read_12v}

    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue

            if command[0] == "quit":
                break
            elif command[0] == "init":
                chassis.init()
                print("Chassis initialized")
            elif command[0] == "scan":
                modules = chassis.iomod.scan_modules()
                print(f"Available modules: {modules}")
            elif command[0] == "select" and len(command) == 2:
                module_id = _parse_module(command[1])
                chassis.iomod.select_module(module_id)
            elif command[0] == "dw" and len(command) == 4:
                module_id, pin, value = _parse_module(command[1]), int(command[2]), int(command[3])
                chassis.iomod.digital_write(module_id, pin, value)
            elif command[0] == "dr" and len(command) == 3:
                module_id, pin = _parse_module(command[1]), int(command[2])
                value = chassis.iomod.digital_read(module_id, pin)
                print(f"Result: {value}")
            elif command[0] == "aw" and len(command) == 4:
                module_id, pin, value = _parse_module(command[1]), int(command[2]), int(command[3])
                chassis.iomod.analog_write(module_id, pin, value)
            elif command[0] == "ar" and len(command) == 3:
                module_id, pin = _parse_module(command[1]), int(command[2])
                value = chassis.iomod.analog_read(module_id, pin)
                print(f"Result: {value}")
            elif command[0] == "pm" and len(command) == 4:
                module_id, pin, mode = _parse_module(command[1]), int(command[2]), int(command[3])
                chassis.iomod.pin_mode(module_id, pin, mode)
            elif command[0] == "vref" and len(command) == 3:
                module_id, activate = _parse_module(command[1]), command[2].lower() == "on"
                chassis.iomod.set_vref(module_id, activate)
            elif command[0] == "reset" and len(command) == 2:
                module_id = _parse_module(command[1])
                chassis.iomod.reset(module_id)
            elif command[0] == "toggle" and len(command) == 3:
                module_id, pin = _parse_module(command[1]), int(command[2])
                chassis.iomod.toggle(module_id, pin)
            elif command[0] == "rail" and len(command) == 3 and command[1] in rails:
                rails[command[1]](command[2].lower() == "on")
            elif command[0] == "power" and len(command) == 2 and command[1] in readings:
                reading = readings[command[1]]()
                print(f"{reading.voltage:.3f}V, {reading.current:.1f}mA, {reading.power:.0f}mW")
            elif command[0] == "button":
                print(f"Pressed: {chassis.button.pressed()}")
            elif command[0] == "beep":
                chassis.beeper.beep(0.1)
            else:
                print("Invalid command or insufficient parameters")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_mode()
    else:
        main()
