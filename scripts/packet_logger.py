#!/usr/bin/env python3
import struct
import argparse
import os
import json
from datetime import datetime

# ATT Opcode Mappings
ATT_OPCODES = {
    0x01: "Error Response",
    0x02: "Exchange MTU Request",
    0x03: "Exchange MTU Response",
    0x04: "Find Information Request",
    0x05: "Find Information Response",
    0x06: "Find By Type Value Request",
    0x07: "Find By Type Value Response",
    0x08: "Read By Type Request",
    0x09: "Read By Type Response",
    0x0A: "Read Request",
    0x0B: "Read Response",
    0x0C: "Read Blob Request",
    0x0D: "Read Blob Response",
    0x0E: "Read Multiple Request",
    0x0F: "Read Multiple Response",
    0x10: "Read By Group Type Request",
    0x11: "Read By Group Type Response",
    0x12: "Write Request",
    0x13: "Write Response",
    0x16: "Prepare Write Request",
    0x17: "Prepare Write Response",
    0x18: "Execute Write Request",
    0x19: "Execute Write Response",
    0x1B: "Handle Value Notification",
    0x1D: "Handle Value Indication",
    0x1E: "Handle Value Confirmation",
    0x52: "Write Command (Write Without Response)",
    0xD2: "Signed Write Command",
}

def parse_btsnoop(file_path: str):
    """
    Parses a binary btsnoop_hci.log file and yields packet dictionaries.
    """
    with open(file_path, "rb") as f:
        # File Header (16 bytes)
        # 8 bytes: Identification Pattern "btsnoop\0"
        # 4 bytes: Version (uint32)
        # 4 bytes: Datalink Type (uint32)
        header = f.read(16)
        if len(header) < 16 or not header.startswith(b"btsnoop\0"):
            raise ValueError("Invalid btsnoop file format: Header signature missing.")
            
        version, datalink = struct.unpack(">II", header[8:])
        
        packet_idx = 0
        while True:
            # Packet Header (24 bytes)
            # 4 bytes: Original Length (uint32)
            # 4 bytes: Included Length (uint32)
            # 4 bytes: Packet Flags (uint32)
            # 4 bytes: Cumulative Drops (uint32)
            # 8 bytes: Timestamp Microseconds (int64)
            pkt_hdr = f.read(24)
            if len(pkt_hdr) < 24:
                break
                
            orig_len, incl_len, flags, drops, ts_us = struct.unpack(">IIIIq", pkt_hdr)
            pkt_data = f.read(incl_len)
            if len(pkt_data) < incl_len:
                break
                
            packet_idx += 1
            
            # Convert timestamp (microseconds since 0001-01-01 to Unix Epoch)
            # 0x00E03AB05702B000 is the microsecond difference from 0001-01-01 to 1970-01-01
            try:
                epoch_us = ts_us - 0x00E03AB05702B000
                dt = datetime.fromtimestamp(epoch_us / 1000000.0)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                time_str = "Unknown"
                
            # Parse packet flags
            # Bit 0: 0 = Sent, 1 = Received (relative to controller)
            # Bit 1: 0 = Data, 1 = Command/Event
            direction = "RX" if (flags & 1) else "TX"
            
            yield {
                "index": packet_idx,
                "timestamp": time_str,
                "direction": direction,
                "data": pkt_data,
                "datalink": datalink
            }

def parse_oppo_frame(payload: bytes) -> dict:
    """
    Decodes the custom OPPO/HeyMelody control protocol frames.
    Format: AA [len] [seq_high] [seq_low] [group] [cmd_id] [seq_id] [payload]
    """
    if len(payload) < 7 or payload[0] != 0xAA:
        return None
    frame_len = payload[1]
    if len(payload) < 2 + frame_len:
        return None
        
    seq = (payload[2] << 8) | payload[3]
    group = payload[4]
    cmd_id = payload[5]
    seq_id = payload[6]
    cmd_payload = payload[7:2+frame_len]
    
    cmd_names = {
        0x01: "Read Request",
        0x02: "Write Command",
        0x04: "Write Command",
        0x05: "Status Notification",
        0x81: "Read Response",
        0x82: "Write Response",
        0x84: "Write Response",
        0x85: "Notification Response"
    }
    cmd_name = cmd_names.get(cmd_id, f"Cmd 0x{cmd_id:02X}")
    
    group_names = {
        0x00: "System Info",
        0x03: "Device Settings Control",
        0x04: "Status Telemetry",
        0x05: "Battery Reporting",
        0x06: "EQ / Battery Control",
        0x07: "Firmware Version",
        0x08: "Touch Gestures",
        0x09: "Firmware Version (Alt)",
        0x0D: "Device Info / Capabilities",
        0x0F: "EQ Status Read",
        0x18: "Device Config",
        0x22: "Handshake Init",
        0x2B: "System Handshake"
    }
    group_name = group_names.get(group, f"Group 0x{group:02X}")
    
    # Decrypting specific payloads
    notes = ""
    hex_pay = cmd_payload.hex().upper()
    
    eq_names = {0: "Original/Balanced", 1: "Bass Boost", 2: "Clear Vocals"}
    
    # EQ Writes: Group 06, Cmd 04
    if group == 0x06 and cmd_id == 0x04:
        if cmd_payload.startswith(b"\x01\x00"):
            val = cmd_payload[2] if len(cmd_payload) > 2 else -1
            notes = f"Write: Set EQ Master to '{eq_names.get(val, f'Unknown ({val})')}'"
    # Battery Query (Modern): Group 06, Cmd 01
    elif group == 0x06 and cmd_id == 0x01:
        notes = "Read: Query Battery Telemetry"
    # EQ Status Response: Group 0F, Cmd 81
    elif group == 0x0F and cmd_id == 0x81:
        if cmd_payload.startswith(b"\x02\x00\x00"):
            val = cmd_payload[3] if len(cmd_payload) > 3 else -1
            notes = f"Read Resp: Current EQ is '{eq_names.get(val, f'Unknown ({val})')}'"
    # State Notifications: Group 04, Cmd 05
    elif group == 0x04 and cmd_id == 0x05:
        if cmd_payload.startswith(b"\x01\x00"):
            val = cmd_payload[2] if len(cmd_payload) > 2 else -1
            notes = f"Notify: EQ updated to '{eq_names.get(val, f'Unknown ({val})')}'"
    # Telemetry push notifications: Group 04, Cmd 02
    elif group == 0x04 and cmd_id == 0x02:
        # cmd_payload here includes the 2-byte payload-length header (e.g. "08 00" or "06 00")
        # that the RFCOMM stream carries but device.py's frame.payload strips. Skip it.
        telem = cmd_payload[2:] if len(cmd_payload) >= 2 else b""
        if len(telem) >= 2:
            report_type = telem[0]
            count = telem[1]
            items = {}
            offset = 2
            for _ in range(count):
                if offset + 2 <= len(telem):
                    item_id = telem[offset]
                    item_val = telem[offset+1]
                    items[item_id] = item_val
                    offset += 2

            if report_type == 0x01:
                # Paradigm A: lower 7 bits = percentage, MSB = charging flag
                def _fmt(raw):
                    if raw == -1:
                        return "?%"
                    pct = raw & 0x7F
                    chg = " \u26a1" if (raw & 0x80) else ""
                    return f"{pct}%{chg}"
                l_val = items.get(1, -1)
                r_val = items.get(2, -1)
                c_val = items.get(3, -1)
                notes = f"Telemetry: Battery Levels (Left={_fmt(l_val)}, Right={_fmt(r_val)}, Case={_fmt(c_val)})"
            elif report_type == 0x02:
                if count == 3:
                    val_names = {0: "Discharging", 1: "Charging", 2: "Full", 3: "Error", 4: "USB/Powered"}
                    l_chg = val_names.get(items.get(1, -1), "Unknown")
                    r_chg = val_names.get(items.get(2, -1), "Unknown")
                    c_chg = val_names.get(items.get(3, -1), "Unknown")
                    notes = f"Telemetry: Charging States (Left={l_chg}, Right={r_chg}, Case={c_chg})"
                elif count == 2:
                    place_names = {0: "In-Case", 1: "Out-of-Case"}
                    l_place = place_names.get(items.get(1, -1), "Unknown")
                    r_place = place_names.get(items.get(2, -1), "Unknown")
                    notes = f"Telemetry: Placement States (Left={l_place}, Right={r_place})"
    # Game Mode Writes: Group 03, Cmd 04
    elif group == 0x03 and cmd_id == 0x04:
        if cmd_payload.startswith(b"\x02\x00\x28"):
            val = cmd_payload[3] if len(cmd_payload) > 3 else -1
            notes = f"Write: Set Game Mode to {'ON' if val == 1 else 'OFF'}"
    # Game Mode Status Response: Group 0D, Cmd 81
    elif group == 0x0D and cmd_id == 0x81:
        if b"\x28\x01" in cmd_payload:
            notes = "Read Resp: Game Mode is ON"
        elif b"\x28\x00" in cmd_payload:
            notes = "Read Resp: Game Mode is OFF"
    # Battery Reporting: Group 05, Cmd 81
    elif group == 0x05 and cmd_id == 0x81:
        if len(cmd_payload) > 4:
            try:
                battery_str = cmd_payload[4:].decode("ascii", errors="ignore")
                parts = battery_str.split(",")
                if len(parts) >= 9:
                    l_state = "Charging" if parts[1] == "2" else "Discharging"
                    l_val = int(parts[2])
                    l_val = l_val - 100 if l_val >= 100 else l_val
                    
                    r_state = "Charging" if parts[4] == "2" else "Discharging"
                    r_val = int(parts[5])
                    r_val = r_val - 100 if r_val >= 100 else r_val
                    
                    c_state = "Charging" if parts[7] == "2" else "Discharging"
                    c_val = int(parts[8])
                    c_val = c_val - 100 if c_val >= 100 else c_val
                    
                    notes = f"Read Resp: Left={l_val}% ({l_state}), Right={r_val}% ({r_state}), Case={c_val}% ({c_state})"
            except Exception:
                pass
    # Battery Reporting (Modern): Group 06, Cmd 81
    elif group == 0x06 and cmd_id == 0x81:
        if len(cmd_payload) >= 4:
            try:
                count = cmd_payload[3]
                items = {}
                offset = 4
                for _ in range(count):
                    if offset + 2 <= len(cmd_payload):
                        item_id = cmd_payload[offset]
                        item_val = cmd_payload[offset+1]
                        items[item_id] = item_val
                        offset += 2
                def _fmt(raw):
                    if raw == -1:
                        return "?%"
                    pct = raw & 0x7F
                    chg = " \u26a1" if (raw & 0x80) else ""
                    return f"{pct}%{chg}"
                l_val = items.get(1, -1)
                r_val = items.get(2, -1)
                c_val = items.get(3, -1)
                notes = f"Read Resp: Left={_fmt(l_val)}, Right={_fmt(r_val)}, Case={_fmt(c_val)}"
            except Exception:
                pass
    # Firmware Version: Group 07/09, Cmd 81
    elif group in [0x07, 0x09] and cmd_id == 0x81:
        if len(cmd_payload) >= 8 and cmd_payload[0] == 0x06:
            v_bytes = cmd_payload[3:8]
            version_str = ".".join(str(b) for b in v_bytes)
            notes = f"Read Resp: Firmware Version is {version_str}"
    # Touch Gestures Configuration: Group 08, Cmd 81
    elif group == 0x08 and cmd_id == 0x81:
        if len(cmd_payload) > 3 and cmd_payload[0] == 98 and cmd_payload[3] == 24:
            notes = f"Read Resp: Loaded 24 touch control gestures configuration matrix"
            
    return {
        "group": f"0x{group:02X}",
        "group_name": group_name,
        "cmd_id": f"0x{cmd_id:02X}",
        "cmd_name": cmd_name,
        "seq_id": f"0x{seq_id:02X}",
        "payload_hex": hex_pay,
        "notes": notes
    }

def extract_gatt_events(packets):
    """
    Processes raw HCI packets to extract L2CAP ATT (GATT) transactions.
    """
    events = []
    
    for pkt in packets:
        data = pkt["data"]
        datalink = pkt["datalink"]
        
        # Android btsnoop logs (both datalink 1001 and 1002) typically prepend
        # the 1-byte HCI packet type. Let's inspect data:
        offset = 0
        if len(data) > 0 and data[0] in [0x01, 0x02, 0x03, 0x04, 0x05]:
            pkt_type = data[0]
            offset = 1
        else:
            pkt_type = 0x02  # Default to ACL data
            
        if len(data) <= offset:
            continue
            
        # HCI ACL Data packet starts here if pkt_type is 0x02
        if pkt_type != 0x02:
            continue
            
        # Parse ACL Header
        # 2 bytes: Connection Handle (12 bits) + PB Flag (2 bits) + BC Flag (2 bits)
        # 2 bytes: Data Total Length (uint16)
        if len(data) < offset + 4:
            continue
            
        handle_flags, acl_len = struct.unpack("<HH", data[offset:offset+4])
        offset += 4
        
        # Parse L2CAP Header
        # 2 bytes: Length
        # 2 bytes: Channel ID (CID)
        if len(data) < offset + 4:
            continue
            
        l2cap_len, cid = struct.unpack("<HH", data[offset:offset+4])
        offset += 4
        
        # 1. Attribute Protocol (ATT / BLE)
        if cid == 0x0004:
            # Parse ATT Protocol Data Unit (PDU)
            # 1 byte: Attribute Opcode
            if len(data) < offset + 1:
                continue
                
            opcode = data[offset]
            opcode_name = ATT_OPCODES.get(opcode, f"Unknown Opcode (0x{opcode:02X})")
            offset += 1
            
            payload = data[offset:]
            
            # Extract handle and value based on opcode structures
            att_handle = None
            att_value = b""
            
            if opcode in [0x0A, 0x12, 0x1B, 0x1D, 0x52]:
                if len(payload) >= 2:
                    att_handle, = struct.unpack("<H", payload[:2])
                    att_value = payload[2:]
            elif opcode == 0x01:
                if len(payload) >= 3:
                    att_handle, = struct.unpack("<H", payload[1:3])
                    att_value = payload[3:]
                    
            hex_val = att_value.hex().upper()
            formatted_hex = " ".join(hex_val[i:i+2] for i in range(0, len(hex_val), 2))
            
            ascii_val = ""
            try:
                ascii_val = "".join(chr(c) for c in att_value if 32 <= c <= 126)
            except Exception:
                pass
                
            events.append({
                "index": pkt["index"],
                "timestamp": pkt["timestamp"],
                "direction": pkt["direction"],
                "type": "BLE GATT",
                "opcode": f"0x{opcode:02X}",
                "opcode_name": f"ATT {opcode_name}",
                "handle": f"0x{att_handle:04X}" if att_handle is not None else "N/A",
                "raw_value": hex_val,
                "formatted_hex": formatted_hex,
                "ascii": ascii_val if len(ascii_val) > 1 else "",
                "notes": "BLE GATT attribute operation."
            })
            
        # 2. RFCOMM (Bluetooth Classic control channel)
        elif cid in [65, 12352]:
            rfcomm_data = data[offset:]
            if len(rfcomm_data) < 3:
                continue
                
            addr = rfcomm_data[0]
            control = rfcomm_data[1]
            len_byte = rfcomm_data[2]
            dlci = addr >> 2
            
            # Only parse the custom control DLCI 30
            if dlci == 30:
                # Parse length
                if len_byte & 1:
                    length = len_byte >> 1
                    rf_offset = 4 if control == 0xff else 3
                    payload = rfcomm_data[rf_offset:rf_offset+length]
                else:
                    if len(rfcomm_data) >= 4:
                        length = (rfcomm_data[3] << 7) | (len_byte >> 1)
                        rf_offset = 5 if control == 0xff else 4
                        payload = rfcomm_data[rf_offset:rf_offset+length]
                    else:
                        payload = b''
                        
                oppo_info = parse_oppo_frame(payload)
                if oppo_info:
                    events.append({
                        "index": pkt["index"],
                        "timestamp": pkt["timestamp"],
                        "direction": pkt["direction"],
                        "type": f"RFCOMM DLCI {dlci}",
                        "opcode": oppo_info["cmd_id"],
                        "opcode_name": f"OPPO {oppo_info['cmd_name']} ({oppo_info['group_name']})",
                        "handle": f"Seq {oppo_info['seq_id']}",
                        "raw_value": oppo_info["payload_hex"],
                        "formatted_hex": " ".join(oppo_info["payload_hex"][i:i+2] for i in range(0, len(oppo_info["payload_hex"]), 2)),
                        "ascii": "",
                        "notes": oppo_info["notes"] if oppo_info["notes"] else f"OPPO Group {oppo_info['group']} transaction"
                    })
        
    return events

def main():
    parser = argparse.ArgumentParser(description="Extract and parse BLE GATT transactions from Android btsnoop_hci.log")
    parser.add_argument("btsnoop_file", help="Path to the binary btsnoop_hci.log file")
    parser.add_argument("--handle", help="Filter events by handle (hex, e.g., 0x001A)")
    parser.add_argument("--opcode", help="Filter events by opcode name substring (e.g. write, notify, read)")
    parser.add_argument("--output", help="Save the output as JSON to the specified path")
    args = parser.parse_args()

    if not os.path.exists(args.btsnoop_file):
        print(f"[-] Error: File not found: {args.btsnoop_file}")
        return
        
    try:
        print(f"[*] Parsing {args.btsnoop_file}...")
        raw_packets = list(parse_btsnoop(args.btsnoop_file))
        print(f"[+] Read {len(raw_packets)} raw packets from log.")
        
        events = extract_gatt_events(raw_packets)
        print(f"[+] Extracted {len(events)} Bluetooth events.")
        
        # Apply filters
        filtered_events = []
        for ev in events:
            if args.handle:
                try:
                    fh = int(args.handle, 16)
                    evh = int(ev["handle"], 16) if ev["handle"] != "N/A" else -1
                    if fh != evh:
                        continue
                except ValueError:
                    # Text match fallback
                    if args.handle.lower() not in ev["handle"].lower():
                        continue
                        
            if args.opcode:
                if args.opcode.lower() not in ev["opcode_name"].lower():
                    continue
                    
            filtered_events.append(ev)
            
        print(f"[+] Displaying {len(filtered_events)} events after filtering:")
        print("-" * 140)
        print(f"{'Time':<26} | {'Dir':<3} | {'Type':<12} | {'Opcode / Event':<40} | {'Handle/Seq':<10} | {'Value (HEX) / Notes'}")
        print("-" * 140)
        
        for ev in filtered_events:
            val_display = ev["formatted_hex"]
            if len(val_display) > 25:
                val_display = val_display[:22] + "..."
            if ev["ascii"]:
                val_display += f" (\"{ev['ascii']}\")"
            if ev.get("notes") and ev["notes"] != "BLE GATT attribute operation.":
                val_display = f"[{val_display}] ➔ {ev['notes']}"
                
            print(f"{ev['timestamp']:<26} | {ev['direction']:<3} | {ev['type']:<12} | {ev['opcode_name']:<40} | {ev['handle']:<10} | {val_display}")
            
        if args.output:
            with open(args.output, "w") as f:
                json.dump(filtered_events, f, indent=4)
            print(f"[+] Saved structured events to: {args.output}")
            
    except Exception as e:
        print(f"[-] Error parsing btsnoop log: {str(e)}")

if __name__ == "__main__":
    main()
