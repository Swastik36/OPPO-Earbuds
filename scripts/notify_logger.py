#!/usr/bin/env python3
import asyncio
import logging
import binascii
import argparse
import os
import sys
import json
from datetime import datetime
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

# Configure console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("notify_logger")

# Map of proprietary Oppo UUIDs for readability in log outputs
OPPO_UUID_NAMES = {
    "0000079a": "OPPO Custom (Fast Pairing/Ecosystem)",
    "0000079c": "OPPO Proprietary (Audio Control/ANC/Gestures)",
    "00000100": "Vendor Specific (Debug/Config)",
    "df21fe2c": "Proprietary Base (OTA)",
    "99999999": "Custom Vendor (Diagnostics)",
}

def get_char_name(uuid_str: str) -> str:
    cleaned = uuid_str.lower().strip()
    for prefix, name in OPPO_UUID_NAMES.items():
        if cleaned.startswith(prefix) or prefix in cleaned:
            return name
    return "Unknown Custom"

def format_data(data: bytearray) -> tuple[str, str]:
    hex_str = binascii.hexlify(data).decode('utf-8').upper()
    formatted_hex = " ".join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
    try:
        ascii_str = data.decode('utf-8').strip()
        printable_ascii = "".join(c for c in ascii_str if c.isprintable())
        if len(printable_ascii) > 2:
            return formatted_hex, printable_ascii
    except UnicodeDecodeError:
        pass
    return formatted_hex, "—"

async def scan_for_oppo_devices():
    logger.info("Scanning for Enco/OPPO BLE devices (5 seconds)...")
    devices = await BleakScanner.discover(timeout=5.0)
    oppo_devices = []
    
    for d in devices:
        name = d.name or "Unknown"
        if "enco" in name.lower() or "oppo" in name.lower() or (d.metadata and d.metadata.get("uuids") and any(uuid.startswith("0000079") for uuid in d.metadata.get("uuids"))):
            oppo_devices.append(d)
            
    if not oppo_devices:
        logger.warning("No OPPO or Enco devices found nearby. Visible devices:")
        for d in devices:
            logger.info(f"    {d.address} - {d.name}")
        return None
        
    logger.info("Found candidate devices:")
    for idx, d in enumerate(oppo_devices):
        logger.info(f"    [{idx}] {d.address} - {d.name}")
        
    return oppo_devices[0].address

async def main():
    parser = argparse.ArgumentParser(description="Real-time BLE Notification Logger for OPPO Enco Buds3 Pro")
    parser.add_argument("address", nargs="?", help="BLE MAC Address of the target device. If not specified, scanner will search.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Connection timeout in seconds")
    parser.add_argument("--scan", action="store_true", help="Force BLE scan to find devices instead of using the default address")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    target_address = args.address
    if not target_address or args.scan:
        target_address = await scan_for_oppo_devices()
        if not target_address:
            target_address = "60:55:56:22:49:A0"
            logger.info(f"Defaulting to documented address: {target_address}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_mac = target_address.replace(":", "-")
    log_filepath = os.path.join(output_dir, f"notifications_{clean_mac}_{timestamp}.jsonl")
    
    logger.info(f"Log file will be written to: {log_filepath}")

    # Open log file in append mode
    log_file = open(log_filepath, "a", encoding="utf-8")

    def notification_handler(sender, data: bytearray):
        # sender is a BleakGATTCharacteristic object
        uuid_str = sender.uuid
        handle = sender.handle
        char_name = get_char_name(uuid_str)
        hex_data, ascii_data = format_data(data)
        
        event_time = datetime.now().isoformat()
        
        # Build log record
        record = {
            "timestamp": event_time,
            "handle": f"0x{handle:04X}",
            "uuid": uuid_str,
            "name": char_name,
            "length": len(data),
            "hex": hex_data,
            "ascii": ascii_data
        }
        
        # Write to JSONL
        log_file.write(json.dumps(record) + "\n")
        log_file.flush()
        
        # Print readable output
        print(f"\n[{event_time}] NOTIFICATION RECEIVED:")
        print(f"  Handle:      0x{handle:04X}")
        print(f"  UUID:        {uuid_str} ({char_name})")
        print(f"  Payload Len: {len(data)} bytes")
        print(f"  HEX:         {hex_data}")
        if ascii_data != "—":
            print(f"  ASCII:       \"{ascii_data}\"")
        print("-" * 50)

    try:
        logger.info(f"Connecting to {target_address}...")
        async with BleakClient(target_address, timeout=args.timeout) as client:
            if not client.is_connected:
                logger.error(f"Failed to connect to {target_address}")
                return
                
            logger.info(f"Connected successfully! Discovering services...")
            services = client.services
            
            subscribed_count = 0
            for service in services:
                for char in service.characteristics:
                    props = char.properties
                    if "notify" in props or "indicate" in props:
                        char_name = get_char_name(char.uuid)
                        logger.info(f"Subscribing to characteristic: Handle: 0x{char.handle:04X} | UUID: {char.uuid} ({char_name}) [Props: {', '.join(props).upper()}]")
                        try:
                            await client.start_notify(char.handle, notification_handler)
                            subscribed_count += 1
                        except Exception as e:
                            logger.error(f"Failed to subscribe to 0x{char.handle:04X}: {str(e)}")
                            
            if subscribed_count == 0:
                logger.warning("No notification-supporting characteristics found or successfully subscribed to.")
            else:
                logger.info(f"Successfully subscribed to {subscribed_count} characteristics. Listening for notifications... Press Ctrl+C to stop.")
                
            # Listen loop until Ctrl+C
            while True:
                await asyncio.sleep(1.0)
                
    except asyncio.CancelledError:
        logger.info("Logging session cancelled by user.")
    except KeyboardInterrupt:
        logger.info("Session stopped. Exiting...")
    except Exception as e:
        logger.error(f"An error occurred during operation: {str(e)}")
    finally:
        log_file.close()
        logger.info("Session finalized. Log file closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
