import argparse
import asyncio
import sys
import os
import time
from .device import OppoDevice, get_friendly_description
from .protocol import OppoFrame
from .commands import EQPreset
from .exceptions import OppoConnectionError, OppoError

async def run_cli(args):
    if args.subcommand == "replay":
        # Offline replay mode: no bluetooth connection required
        if not os.path.exists(args.file):
            print(f"[-] Error: Log file '{args.file}' does not exist.", file=sys.stderr)
            sys.exit(1)
            
        print(f"[+] Replaying session log: {args.file}\n")
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("---"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    ts, direction, raw_hex = parts[0], parts[1], parts[2]
                    try:
                        raw_data = bytes.fromhex(raw_hex)
                        frame = OppoFrame.from_bytes(raw_data)
                        desc = get_friendly_description(frame)
                        print(f"[{ts}] {direction} ➔ {raw_hex} | {desc}")
                    except Exception as e:
                        print(f"[{ts}] {direction} ➔ {raw_hex} | Parsing Failed ({e})")
        return

    # Connection-based commands
    record_file = args.file if args.subcommand == "record" else None
    
    try:
        async with OppoDevice(mac_address=args.mac, trace_mode=args.trace, record_file=record_file) as device:
            if args.subcommand == "record":
                print(f"[+] Recording session to: {args.file}")
                print("[+] Polling device status every 2 seconds. Press Ctrl+C to stop...\n")
                try:
                    # Fetch initial status to populate version info
                    await device.get_firmware()
                    await device.get_gestures()
                    
                    while True:
                        # Poll battery and settings to generate traffic
                        await device.get_battery()
                        await device.get_eq()
                        await device.get_game_mode()
                        await device.get_volume()
                        await asyncio.sleep(2)
                except asyncio.CancelledError:
                    pass
                return

            if args.subcommand == "battery":
                bat = await device.get_battery_status()
                print(f"Left Earbud:   {bat.left}% [Charging={bat.left.is_charging}]")
                print(f"Right Earbud:  {bat.right}% [Charging={bat.right.is_charging}]")
                print(f"Charging Case: {bat.case}% [Charging={bat.case.is_charging}]" if bat.case != -1 else "Charging Case: Disconnected")
                
            elif args.subcommand == "anc":
                await device.set_anc_mode(args.mode)
                print(f"[+] Active Noise Cancelling successfully set to: {args.mode.upper()}")
                
            elif args.subcommand == "eq":
                preset = EQPreset[args.preset.upper()]
                await device.set_equalizer(preset)
                print(f"[+] Equalizer hardware register updated to profile: {args.preset.upper()}")

            elif args.subcommand == "gamemode":
                enable = args.state == "on"
                await device.set_game_mode(enable)
                print(f"[+] Game Mode updated to: {args.state.upper()}")

            elif args.subcommand == "gestures":
                gestures = await device.get_gestures()
                print(f"[+] Loaded {len(gestures)} Touch Gestures from hardware matrix:")
                for gesture in gestures:
                    print(f"  ➔ {gesture}")

            elif args.subcommand == "find":
                start = args.action == "start"
                await device.find_device(start)
                state_str = "STARTED" if start else "STOPPED"
                print(f"[+] Find My Device alert tone successfully {state_str}")

            elif args.subcommand == "volume":
                if args.value is None:
                    vol = await device.get_volume()
                    print(f"Prompt Alert Volume: {vol}%")
                else:
                    await device.set_volume(args.value)
                    print(f"[+] Prompt Alert Volume updated to: {args.value}%")

            elif args.subcommand == "info":
                fw = await device.get_firmware()
                print(f"Device MAC:       {device.mac_address}")
                print(f"Firmware Version: {fw}")
                
    except OppoConnectionError as err:
        print(f"[-] Execution Failure: {err}", file=sys.stderr)
        sys.exit(1)
    except OppoError as err:
        print(f"[-] Command Failure: {err}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[+] Recording stopped cleanly.")
        sys.exit(0)
    except Exception as err:
        print(f"[-] Unexpected Error: {err}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(prog="oppoctl", description="OPPO Enco Buds3 Pro Hardware Control Utility")
    parser.add_argument("--mac", default="60:55:56:22:49:A0", help="Target Bluetooth hardware address mapping")
    parser.add_argument("--trace", action="store_true", help="Enable raw TX/RX packet trace diagnostics")
    
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.add_parser("battery", help="Query real-time capacity states")
    
    anc_parser = subparsers.add_parser("anc", help="Modify peripheral environmental acoustic dampening profiles")
    anc_parser.add_argument("mode", choices=["on", "off", "transparency"], help="Target operational state")
    
    eq_parser = subparsers.add_parser("eq", help="Reconfigure hardware DSP profiles")
    eq_parser.add_argument("preset", choices=["original", "bass", "treble", "vocal", "bass_boost", "treble_boost"], help="Target optimization layout")

    gm_parser = subparsers.add_parser("gamemode", help="Toggle Low Latency Game Mode")
    gm_parser.add_argument("state", choices=["on", "off"], help="Target Game Mode state")

    subparsers.add_parser("gestures", help="Dump Touch Gestures configuration matrix")
    
    find_parser = subparsers.add_parser("find", help="Toggle ringing alert to locate earbuds")
    find_parser.add_argument("action", choices=["start", "stop"], help="Start or stop ringing alert")

    vol_parser = subparsers.add_parser("volume", help="Query or set system prompt tone volume")
    vol_parser.add_argument("value", type=int, nargs="?", help="Optional volume percentage (0-100) to set")

    # Record Subcommand
    rec_parser = subparsers.add_parser("record", help="Record connection session packets to a log file")
    rec_parser.add_argument("file", help="Output session log filepath (e.g. session.oplog)")

    # Replay Subcommand
    rep_parser = subparsers.add_parser("replay", help="Offline parse and replay recorded session logs")
    rep_parser.add_argument("file", help="Input session log filepath")

    subparsers.add_parser("info", help="Query device hardware and firmware specifications")
    
    args = parser.parse_args()
    
    # Custom validation for volume range
    if args.subcommand == "volume" and args.value is not None:
        if not (0 <= args.value <= 100):
            print("[-] Error: Volume percentage must be between 0 and 100", file=sys.stderr)
            sys.exit(1)
            
    asyncio.run(run_cli(args))

if __name__ == "__main__":
    main()
