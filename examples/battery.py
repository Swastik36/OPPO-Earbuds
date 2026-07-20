import asyncio
import sys
from oppo_control import OppoDevice

async def main():
    mac = "60:55:56:22:49:A0"
    if len(sys.argv) > 1:
        mac = sys.argv[1]
        
    print(f"Connecting to {mac}...")
    try:
        async with OppoDevice(mac_address=mac) as device:
            battery = await device.get_battery_status()
            print(f"[+] Connected to: {device.profile.name}")
            print(f"  ➔ Left Bud:   {battery.left}% [Charging={battery.left.is_charging}]")
            print(f"  ➔ Right Bud:  {battery.right}% [Charging={battery.right.is_charging}]")
            if battery.case != -1:
                print(f"  ➔ Case:       {battery.case}% [Charging={battery.case.is_charging}]")
            else:
                print("  ➔ Case:       Disconnected")
    except Exception as e:
        print(f"[-] Failed to fetch battery status: {e}")

if __name__ == "__main__":
    asyncio.run(main())
