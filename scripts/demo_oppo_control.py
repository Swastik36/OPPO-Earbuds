import asyncio
import sys
import os

# Add src/ directory to system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from oppo_control import OppoDevice, EQPreset

# Setup clean logging
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    device = OppoDevice("60:55:56:22:49:A0", port=15)
    
    print("[*] Connecting to Oppo Enco Buds3 Pro...")
    await device.connect()
    print("[+] Connected successfully!\n")

    # Define event callback
    def on_event(event_type, data):
        print(f"\n🚨 EVENT PUSHED: Type={event_type}, Data={data}\n")
    device.register_callback(on_event)

    # 1. Get Battery
    battery = await device.get_battery()
    print(f"[+] Battery Telemetry:")
    print(f"  ➔ Left:  {battery.left.percentage}% [Charging={battery.left.is_charging}]")
    print(f"  ➔ Right: {battery.right.percentage}% [Charging={battery.right.is_charging}]")
    print(f"  ➔ Case:  {battery.case.percentage}% [Charging={battery.case.is_charging}]\n")

    # 2. Get Firmware Version
    fw = await device.get_firmware()
    print(f"[+] Firmware Version: {fw}\n")

    # 3. Get EQ Preset
    eq = await device.get_eq()
    print(f"[+] Current EQ Preset: {eq.name}\n")

    # 4. Set EQ to Bass
    print("[*] Toggling EQ to BASS...")
    await device.set_eq(EQPreset.BASS)
    
    # Sleep briefly to observe the notification event callback
    await asyncio.sleep(0.5)

    # Read back to verify
    eq = await device.get_eq()
    print(f"[+] Verified EQ Preset: {eq.name}\n")

    # 5. Read Game Mode status
    game_mode = await device.get_game_mode()
    print(f"[+] Current Game Mode: {'ON' if game_mode else 'OFF'}\n")

    # 6. Toggle Game Mode
    target_gm = not game_mode
    print(f"[*] Setting Game Mode to: {'ON' if target_gm else 'OFF'}...")
    await device.set_game_mode(target_gm)
    
    await asyncio.sleep(0.5)

    # Read back to verify
    game_mode = await device.get_game_mode()
    print(f"[+] Verified Game Mode: {'ON' if game_mode else 'OFF'}\n")

    # 7. Restore EQ to balanced
    print("[*] Restoring EQ to Balanced (Original)...")
    await device.set_eq(EQPreset.ORIGINAL)
    
    await asyncio.sleep(0.5)

    # 8. Load Gestures
    gestures = await device.get_gestures()
    print(f"[+] Loaded {len(gestures)} Gestures from Earbud Config Matrix (First 6 shown):")
    for gesture in gestures[:6]:
        print(f"  ➔ {gesture}")

    print("\n[*] Disconnecting...")
    await device.disconnect()
    print("[+] Done.")

if __name__ == "__main__":
    asyncio.run(main())
