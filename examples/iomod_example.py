#!/usr/bin/env python3
"""
IOMod Library Example Usage

This example demonstrates how to use the IOMod library to control multiple
AD5593R modules through a TCA9548A I2C multiplexer.

Hardware setup:
- TCA9548A I2C multiplexer connected to I2C bus
- Multiple AD5593R modules connected to different channels of the multiplexer
- Each AD5593R should be configured with address 0x10
"""

import time
import iomod

def main():
    """Main example function"""
    print("IOMod Library Example")
    print("====================")
    
    try:
        # Initialize the IOMod system
        print("Initializing IOMod system...")
        iomod.init()
        
        # Scan for available modules
        print("\nScanning for available modules...")
        available_modules = iomod.scan_modules()
        
        if not available_modules:
            print("No modules found! Check your hardware connections.")
            return
        
        print(f"Found {len(available_modules)} available modules: {available_modules}")
        
        # Use the first available module for demonstration
        module_id = available_modules[0]
        print(f"\nUsing module {module_id} for demonstration")
        
        # Example 1: Digital I/O operations
        print("\n--- Digital I/O Example ---")
        
        # Configure pin 2 as digital output
        print("Configuring pin 2 as digital output...")
        iomod.pinmode(module_id, 2, iomod.OUTPUT)
        
        # Toggle the pin 5 times
        print("Toggling pin 2 five times...")
        for i in range(5):
            iomod.digitalwrite(module_id, 2, iomod.HIGH)
            print(f"  Iteration {i+1}: Pin 2 = HIGH")
            time.sleep(0.5)
            
            iomod.digitalwrite(module_id, 2, iomod.LOW)
            print(f"  Iteration {i+1}: Pin 2 = LOW")
            time.sleep(0.5)
        
        # Example 2: Digital input
        print("\n--- Digital Input Example ---")
        
        # Configure pin 1 as digital input
        print("Configuring pin 1 as digital input...")
        iomod.pinmode(module_id, 1, iomod.INPUT)
        
        # Read the pin 10 times
        print("Reading pin 1 ten times...")
        for i in range(10):
            value = iomod.digitalread(module_id, 1)
            print(f"  Reading {i+1}: Pin 1 = {'HIGH' if value else 'LOW'}")
            time.sleep(0.2)
        
        # Example 3: Analog operations
        print("\n--- Analog Operations Example ---")
        
        # Enable voltage reference
        print("Enabling voltage reference...")
        iomod.setvref(module_id, True)
        vref = iomod.getvref(module_id)
        print(f"Reference voltage: {vref:.2f}V")
        
        # Configure pin 3 as ADC input
        print("Configuring pin 3 as ADC input...")
        iomod.pinmode(module_id, 3, iomod.ADC)
        
        # Read analog values
        print("Reading analog values from pin 3...")
        for i in range(5):
            raw_value = iomod.analogread(module_id, 3, average=3)
            voltage = iomod.readvoltage(module_id, 3, average=3)
            print(f"  Reading {i+1}: Raw = {raw_value}, Voltage = {voltage:.3f}V")
            time.sleep(0.5)
        
        # Configure pin 4 as DAC output
        print("Configuring pin 4 as DAC output...")
        iomod.pinmode(module_id, 4, iomod.DAC)
        
        # Write different DAC values
        print("Writing different DAC values to pin 4...")
        test_values = [0, 1024, 2048, 3072, 4095]  # 0%, 25%, 50%, 75%, 100%
        
        for i, value in enumerate(test_values):
            iomod.analogwrite(module_id, 4, value)
            expected_voltage = (value / 4095) * vref
            print(f"  DAC {i+1}: Value = {value}, Expected Voltage = {expected_voltage:.3f}V")
            time.sleep(1)
        
        # Reset to 0V
        iomod.analogwrite(module_id, 4, 0)
        print("DAC reset to 0V")
        
        # Example 4: Multiple modules (if available)
        if len(available_modules) > 1:
            print(f"\n--- Multiple Modules Example ---")
            print(f"Testing with modules: {available_modules[:2]}")
            
            for i, mod_id in enumerate(available_modules[:2]):
                print(f"\nTesting module {mod_id}:")
                
                # Configure pin 0 as output
                iomod.pinmode(mod_id, 0, iomod.OUTPUT)
                
                # Write different states
                state = i % 2  # Alternate between HIGH and LOW
                iomod.digitalwrite(mod_id, 0, state)
                print(f"  Module {mod_id}, Pin 0: {'HIGH' if state else 'LOW'}")
        
        # Example 5: Using select_module for convenience
        print(f"\n--- Module Selection Example ---")
        print(f"Selecting module {module_id}...")
        iomod.select_module(module_id)
        
        # Now we can use the selected module without specifying module_id
        # (Note: This is a conceptual example - the current implementation
        # still requires module_id in function calls)
        
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
    print("  init                    - Initialize IOMod system")
    print("  scan                    - Scan for available modules")
    print("  select <module>         - Select a module")
    print("  dw <module> <pin> <val> - Digital write (val: 0 or 1)")
    print("  dr <module> <pin>       - Digital read")
    print("  aw <module> <pin> <val> - Analog write (val: 0-4095)")
    print("  ar <module> <pin>       - Analog read")
    print("  pm <module> <pin> <mode>- Pin mode (mode: 1=INPUT, 2=OUTPUT, 3=ADC, 4=DAC)")
    print("  vref <module> <on/off>  - Set voltage reference")
    print("  reset <module>          - Reset module")
    print("  toggle <module> <pin>   - Toggle digital output")
    print("  quit                    - Exit")

    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue

            if command[0] == "quit":
                break
            elif command[0] == "init":
                iomod.init()
                print("IOMod system initialized")
            elif command[0] == "scan":
                modules = iomod.scan_modules()
                print(f"Available modules: {modules}")
            elif command[0] == "select" and len(command) == 2:
                module_id = _parse_module(command[1])
                iomod.select_module(module_id)
            elif command[0] == "dw" and len(command) == 4:
                module_id, pin, value = _parse_module(command[1]), int(command[2]), int(command[3])
                iomod.digitalwrite(module_id, pin, value)
            elif command[0] == "dr" and len(command) == 3:
                module_id, pin = _parse_module(command[1]), int(command[2])
                value = iomod.digitalread(module_id, pin)
                print(f"Result: {value}")
            elif command[0] == "aw" and len(command) == 4:
                module_id, pin, value = _parse_module(command[1]), int(command[2]), int(command[3])
                iomod.analogwrite(module_id, pin, value)
            elif command[0] == "ar" and len(command) == 3:
                module_id, pin = _parse_module(command[1]), int(command[2])
                value = iomod.analogread(module_id, pin)
                print(f"Result: {value}")
            elif command[0] == "pm" and len(command) == 4:
                module_id, pin, mode = _parse_module(command[1]), int(command[2]), int(command[3])
                iomod.pinmode(module_id, pin, mode)
            elif command[0] == "vref" and len(command) == 3:
                module_id, activate = _parse_module(command[1]), command[2].lower() == "on"
                iomod.setvref(module_id, activate)
            elif command[0] == "reset" and len(command) == 2:
                module_id = _parse_module(command[1])
                iomod.reset_module(module_id)
            elif command[0] == "toggle" and len(command) == 3:
                module_id, pin = _parse_module(command[1]), int(command[2])
                iomod.toggle(module_id, pin)
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
