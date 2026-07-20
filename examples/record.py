import asyncio
import sys
from oppo_control import OppoDevice

async def main():
    mac = "60:55:56:22:49:A0"
    log_file = "examples_session.oplog"
    if len(sys.argv) > 1:
        mac = sys.argv[1]
    if len(sys.argv) > 2:
        log_file = sys.argv[2]
        
    print(f"Connecting to {mac} and writing session packets to: {log_file}...")
    print("Will run for 10 seconds to collect packets...")
    try:
        async with OppoDevice(mac_address=mac, record_file=log_file) as device:
            # Query standard features to generate initial transaction entries
            await device.get_firmware()
            await device.get_battery()
            await device.get_eq()
            await device.get_game_mode()
            
            # Wait for 10 seconds to capture any push notifications or polling traffic
            await asyncio.sleep(10)
            print(f"[+] Successfully wrote trace logging records to: {log_file}")
    except Exception as e:
        print(f"[-] Session recording failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
