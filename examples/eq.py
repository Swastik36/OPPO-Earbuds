import asyncio
import sys
from oppo_control import OppoDevice, EQPreset

async def main():
    mac = "60:55:56:22:49:A0"
    if len(sys.argv) > 1:
        mac = sys.argv[1]
        
    print(f"Connecting to {mac}...")
    try:
        async with OppoDevice(mac_address=mac) as device:
            # Query active hardware EQ preset
            current_eq = await device.get_eq()
            print(f"[+] Current EQ Preset: {current_eq.name}")
            
            # Reconfigure DSP to Bass Boost preset
            print("[+] Writing 'Bass Boost' profile to hardware register...")
            await device.set_equalizer(EQPreset.BASS_BOOST)
            
            # Verify update
            updated_eq = await device.get_eq()
            print(f"[+] Updated EQ Preset: {updated_eq.name}")
    except Exception as e:
        print(f"[-] Failed to configure EQ preset: {e}")

if __name__ == "__main__":
    asyncio.run(main())
