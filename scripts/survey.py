#!/usr/bin/env python3
import asyncio
import logging
import binascii
import argparse
import os
import json
from datetime import datetime
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

# Architectural Mapping Tables
STANDARD_SIG_UUIDS = {
    # Services
    "1800": "Generic Access Service",
    "1801": "Generic Attribute Service",
    "180a": "Device Information Service",
    "180f": "Battery Service",
    "1812": "Human Interface Device",
    # Characteristics
    "2a00": "Device Name",
    "2a01": "Appearance",
    "2a02": "Peripheral Privacy Flag",
    "2a03": "Reconnection Address",
    "2a04": "Peripheral Preferred Connection Parameters",
    "2a05": "Service Changed",
    "2a24": "Model Number String",
    "2a25": "Serial Number String",
    "2a26": "Firmware Revision String",
    "2a27": "Hardware Revision String",
    "2a28": "Software Revision String",
    "2a29": "Manufacturer Name String",
    "2a19": "Battery Level",
    # Descriptors
    "2901": "Characteristic User Description",
    "2902": "Client Characteristic Configuration Descriptor (CCCD)",
}

OPPO_PROPRIETARY_MAP = {
    "0000079a": "OPPO Custom Service (Fast Pairing/Ecosystem)",
    "0000079c": "OPPO Proprietary Service (Audio Control/ANC/Gestures)",
    "00000100": "Vendor Specific Service (Debug/Manufacturing Config)",
    "df21fe2c": "Proprietary Base Service (OTA Firmware Update)",
    "99999999": "Custom Vendor Service (Diagnostics/Secondary Telemetry)",
}

def analyze_uuid(uuid_str: str) -> tuple[str, str, str]:
    """
    Analyzes a given UUID string to determine its origin, type, and hypothesis notes.
    """
    cleaned_uuid = uuid_str.lower().strip()
    
    # Check short-form standard SIG match
    for sig_short, name in STANDARD_SIG_UUIDS.items():
        if cleaned_uuid.startswith(f"0000{sig_short}") or sig_short == cleaned_uuid:
            return "✅ Standard", name, "Adheres to official Bluetooth SIG Specifications."
            
    # Check known proprietary signatures
    for prop_prefix, name in OPPO_PROPRIETARY_MAP.items():
        if cleaned_uuid.startswith(prop_prefix) or prop_prefix in cleaned_uuid:
            return "⚠️ Proprietary", name, "Vendor-specific endpoint. Requires protocol analysis."
            
    # Fallback for undocumented custom 128-bit UUIDs
    if len(cleaned_uuid) > 8 and not cleaned_uuid.endswith("00805f9b34fb"):
        return "❓ Proprietary (Unmapped)", "Unknown Vendor Characteristic", "Hypothesis: Custom payload/diagnostic channel."
        
    return "❓ Unknown", "Unknown Profile", "Unclassified GATT attribute."

def safe_decode_value(raw_bytes: bytearray) -> tuple[str, str]:
    """
    Attempts to decode raw byte buffers into printable ASCII text and hex strings.
    Returns (raw_hex, formatted_display_string)
    """
    if not raw_bytes:
        return "", "N/A"
    hex_str = binascii.hexlify(raw_bytes).decode('utf-8').upper()
    formatted_hex = "0x" + hex_str
    
    try:
        ascii_str = raw_bytes.decode('utf-8').strip()
        printable_ascii = "".join(c for c in ascii_str if c.isprintable())
        if len(printable_ascii) > 2:
            return hex_str, f"Hex: [0x{hex_str}] | ASCII: \"{printable_ascii}\""
    except UnicodeDecodeError:
        pass
        
    return hex_str, formatted_hex

async def scan_for_oppo_devices():
    """
    Scans for BLE devices and returns the address of the first OPPO device found.
    """
    print("[*] Scanning for BLE devices (5 seconds)...")
    devices = await BleakScanner.discover(timeout=5.0)
    oppo_devices = []
    
    for d in devices:
        name = d.name or "Unknown"
        # Match against common patterns
        if "enco" in name.lower() or "oppo" in name.lower() or (d.metadata and d.metadata.get("uuids") and any(uuid.startswith("0000079") for uuid in d.metadata.get("uuids"))):
            oppo_devices.append(d)
            
    if not oppo_devices:
        print("[-] No OPPO or Enco devices found nearby. Here are the visible devices:")
        for d in devices:
            print(f"    {d.address} - {d.name}")
        return None
        
    print("[+] Found candidate devices:")
    for idx, d in enumerate(oppo_devices):
        print(f"    [{idx}] {d.address} - {d.name}")
        
    # Return the first one
    return oppo_devices[0].address

async def run_gatt_survey(address: str, timeout: float, output_dir: str, docs_dir: str):
    """
    Executes a structured GATT survey on the target device, prints results,
    and writes them to Markdown and JSON outputs.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"================================================================================")
    print(f"INITIALIZING GATT SURVEY FOR: {address} at {timestamp}")
    print(f"================================================================================")
    
    try:
        async with BleakClient(address, timeout=timeout) as client:
            if not client.is_connected:
                print(f"[-] Critical Error: Failed to secure connection to {address}")
                return
                
            print(f"[+] Connection successfully stabilized. Querying complete GATT Hierarchy...")
            services = client.services
            
            gatt_data = {
                "device_address": address,
                "timestamp": timestamp,
                "services": []
            }
            
            markdown_rows = []
            
            # Formulate Markdown Header
            headers = ["Handle", "Type", "UUID", "Name / Purpose", "Properties", "Status", "Value / Context", "Notes"]
            row_format = "| {:<8} | {:<14} | {:<36} | {:<45} | {:<30} | {:<12} | {:<35} | {:<45} |"
            
            print("\n[+] Mapping complete database structure. Compiling data matrices...\n")
            
            for service in services:
                status, name, note = analyze_uuid(service.uuid)
                service_entry = {
                    "handle": service.handle,
                    "uuid": service.uuid,
                    "name": name,
                    "status": status,
                    "notes": note,
                    "characteristics": []
                }
                
                markdown_rows.append({
                    "handle": f"0x{service.handle:04X}",
                    "type": "Primary Service",
                    "uuid": service.uuid,
                    "name": name,
                    "properties": "—",
                    "status": status,
                    "value": "—",
                    "notes": note
                })
                
                for char in service.characteristics:
                    props_list = char.properties
                    props_str = ", ".join(props_list).upper()
                    status, name, note = analyze_uuid(char.uuid)
                    
                    if status != "✅ Standard":
                        if "NOTIFY" in props_list or "INDICATE" in props_list:
                            note = "Hypothesis: Proprietary asynchronous events / State telemetry stream."
                        elif "WRITE" in props_list or "WRITE-WITHOUT-RESPONSE" in props_list:
                            if "READ" not in props_list:
                                note = "Hypothesis: Pure custom Command/Control RX plane."
                            else:
                                note = "Hypothesis: Bi-directional control and configuration register."
                    
                    val_str = "Unreadable / No Read Perms"
                    raw_hex = ""
                    read_status = "not_readable"
                    
                    if "read" in props_list:
                        try:
                            raw_val = await asyncio.wait_for(client.read_gatt_char(char.handle), timeout=5.0)
                            raw_hex, val_str = safe_decode_value(raw_val)
                            read_status = "success"
                            if "ASCII" in val_str and name == "Unknown Vendor Characteristic":
                                note = "Observed plain text metadata transmission."
                        except asyncio.TimeoutError:
                            val_str = "⚠️ Read Timeout Error"
                            read_status = "timeout"
                        except BleakError as be:
                            err_msg = str(be).lower()
                            if "insufficient authentication" in err_msg or "encryption" in err_msg:
                                val_str = "⚠️ Authentication Required"
                                read_status = "auth_required"
                            elif "permission" in err_msg:
                                val_str = "⚠️ Permission Denied"
                                read_status = "permission_denied"
                            else:
                                val_str = f"⚠️ Bleak Error: {str(be)}"
                                read_status = f"error: {str(be)}"
                        except Exception as e:
                            val_str = f"⚠️ Read Blocked: {str(e)}"
                            read_status = f"error: {str(e)}"
                            
                    char_entry = {
                        "handle": char.handle,
                        "uuid": char.uuid,
                        "name": name,
                        "properties": props_list,
                        "status": status,
                        "notes": note,
                        "read_status": read_status,
                        "value_hex": raw_hex,
                        "value_display": val_str,
                        "descriptors": []
                    }
                    
                    markdown_rows.append({
                        "handle": f"0x{char.handle:04X}",
                        "type": "Characteristic",
                        "uuid": char.uuid,
                        "name": name,
                        "properties": props_str,
                        "status": status,
                        "value": val_str,
                        "notes": note
                    })
                    
                    for desc in char.descriptors:
                        status, name, note = analyze_uuid(desc.uuid)
                        desc_val_str = "N/A"
                        desc_hex = ""
                        desc_read_status = "not_readable"
                        
                        try:
                            raw_desc_val = await asyncio.wait_for(client.read_gatt_descriptor(desc.handle), timeout=2.0)
                            desc_hex, desc_val_str = safe_decode_value(raw_desc_val)
                            desc_read_status = "success"
                        except Exception as e:
                            desc_read_status = f"error: {str(e)}"
                            
                        char_entry["descriptors"].append({
                            "handle": desc.handle,
                            "uuid": desc.uuid,
                            "name": name,
                            "status": status,
                            "read_status": desc_read_status,
                            "value_hex": desc_hex,
                            "value_display": desc_val_str,
                            "notes": note
                        })
                        
                        markdown_rows.append({
                            "handle": f"0x{desc.handle:04X}",
                            "type": "Descriptor",
                            "uuid": desc.uuid,
                            "name": name,
                            "properties": "READ/WRITE (Implicit)",
                            "status": status,
                            "value": desc_val_str,
                            "notes": note
                        })
                        
                    service_entry["characteristics"].append(char_entry)
                gatt_data["services"].append(service_entry)

            # Output the generated Markdown Table in stdout
            print("# GATT Profile & Technical Map: OPPO Enco Buds3 Pro\n")
            print(row_format.format(*headers))
            print(row_format.format(*["-"*8, "-"*14, "-"*36, "-"*45, "-"*30, "-"*12, "-"*35, "-"*45]))
            
            for row in markdown_rows:
                truncated_value = row["value"][:32] + "..." if len(row["value"]) > 35 else row["value"]
                truncated_notes = row["notes"][:42] + "..." if len(row["notes"]) > 45 else row["notes"]
                truncated_name = row["name"][:42] + "..." if len(row["name"]) > 45 else row["name"]
                
                print(row_format.format(
                    row["handle"],
                    row["type"],
                    row["uuid"],
                    truncated_name,
                    row["properties"],
                    row["status"],
                    truncated_value,
                    truncated_notes
                ))
                
            print(f"\n================================================================================")
            
            # Save files
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(docs_dir, exist_ok=True)
            
            # 1. Save JSON Dump
            json_filename = f"gatt_survey_{timestamp}.json"
            json_filepath = os.path.join(output_dir, json_filename)
            with open(json_filepath, "w") as f:
                json.dump(gatt_data, f, indent=4)
            print(f"[+] Saved JSON structural dump to: {json_filepath}")
            
            # Keep latest reference JSON
            latest_json_path = os.path.join(output_dir, "latest_gatt.json")
            with open(latest_json_path, "w") as f:
                json.dump(gatt_data, f, indent=4)
                
            # 2. Save Markdown Report to docs/GATT_PROFILE.md
            md_filepath = os.path.join(docs_dir, "GATT_PROFILE.md")
            
            with open(md_filepath, "w") as f:
                f.write(f"# GATT Profile & Technical Map: OPPO Enco Buds3 Pro\n\n")
                f.write(f"* **Survey Timestamp:** {timestamp}\n")
                f.write(f"* **Target Device MAC Address:** `{address}`\n\n")
                f.write(f"| Handle | Type | UUID | Name / Purpose | Properties | Status | Value / Context | Notes |\n")
                f.write(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for row in markdown_rows:
                    f.write(f"| {row['handle']} | {row['type']} | `{row['uuid']}` | {row['name']} | {row['properties']} | {row['status']} | `{row['value']}` | {row['notes']} |\n")
            print(f"[+] Saved updated Markdown documentation to: {md_filepath}")
            
            # Also save a timestamped copy of the markdown report in output
            timestamped_md_path = os.path.join(output_dir, f"gatt_profile_{timestamp}.md")
            with open(timestamped_md_path, "w") as f:
                with open(md_filepath, "r") as ref:
                    f.write(ref.read())
            print(f"[+] Saved timestamped Markdown copy to: {timestamped_md_path}")
            
            print(f"================================================================================")

    except Exception as e:
        print(f"[-] A critical runtime survey error occurred: {str(e)}")

async def main():
    parser = argparse.ArgumentParser(description="Structured BLE GATT Survey Tool for OPPO Enco Buds3 Pro")
    parser.add_argument("address", nargs="?", help="BLE MAC Address of the target device. If not specified, scanner will search for Enco/OPPO devices.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Connection timeout in seconds")
    parser.add_argument("--scan", action="store_true", help="Force BLE scan to find devices instead of using the default address")
    args = parser.parse_args()

    # Determine paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    docs_dir = os.path.join(project_root, "docs")
    output_dir = os.path.join(project_root, "output")

    target_address = args.address
    if not target_address or args.scan:
        target_address = await scan_for_oppo_devices()
        if not target_address:
            # Fallback to the default address from documentation
            target_address = "60:55:56:22:49:A0"
            print(f"[*] Defaulting to documented address: {target_address}")
            
    await run_gatt_survey(target_address, args.timeout, output_dir, docs_dir)

if __name__ == "__main__":
    asyncio.run(main())
