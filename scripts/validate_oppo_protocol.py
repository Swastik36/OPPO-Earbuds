import socket
import time
import sys

DEVICE_MAC = "60:55:56:22:49:A0"
PORT = 15 # DLCI 30

def print_hex(label, data):
    hex_str = " ".join(f"{b:02X}" for b in data)
    print(f"{label:<12} | Hex: {hex_str} | ASCII: {repr(data)}")

def make_frame(group, cmd_id, seq_id, payload=b""):
    # AA [len] 00 00 [group] [cmd_id] [seq_id] [payload]
    header = struct.pack(">B", 0xAA)
    rem_len = 5 + len(payload)
    frame = bytearray([0xAA, rem_len, 0x00, 0x00, group, cmd_id, seq_id]) + payload
    return bytes(frame)

def parse_response(data):
    if len(data) < 7 or data[0] != 0xAA:
        return None
    length = data[1]
    if len(data) < 2 + length:
        return None
    
    group = data[4]
    cmd_id = data[5]
    seq_id = data[6]
    payload = data[7:2+length]
    return {
        "group": group,
        "cmd_id": cmd_id,
        "seq_id": seq_id,
        "payload": payload
    }

def main():
    print(f"[*] Connecting to {DEVICE_MAC} on RFCOMM port {PORT}...")
    try:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(3.0)
        s.connect((DEVICE_MAC, PORT))
        print("[+] RFCOMM Connection established successfully!")
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)

    try:
        # 1. Read Battery
        # AA 07 00 00 05 01 01 00 00
        battery_req = bytes([0xAA, 0x07, 0x00, 0x00, 0x05, 0x01, 0x01, 0x00, 0x00])
        print_hex("\n[TX] Battery", battery_req)
        s.send(battery_req)
        
        # Read response
        resp = s.recv(1024)
        print_hex("[RX] Battery", resp)
        parsed = parse_response(resp)
        if parsed and parsed["group"] == 0x05:
            try:
                battery_str = parsed["payload"][4:].decode("ascii")
                print(f"  ➔ Parsed Battery Telemetry CSV: {battery_str}")
            except Exception as e:
                print(f"  ➔ Error decoding battery payload: {e}")

        time.sleep(0.5)

        # 2. Read Firmware Version
        # AA 07 00 00 07 01 02 00 00
        fw_req = bytes([0xAA, 0x07, 0x00, 0x00, 0x07, 0x01, 0x02, 0x00, 0x00])
        print_hex("\n[TX] Version", fw_req)
        s.send(fw_req)
        
        resp = s.recv(1024)
        print_hex("[RX] Version", resp)
        parsed = parse_response(resp)
        if parsed and parsed["group"] == 0x07:
            # payload is e.g. 06 00 00 02 01 01 02 01
            v_bytes = parsed["payload"][3:8]
            version_str = ".".join(str(b) for b in v_bytes) if len(v_bytes) >= 5 else "Unknown"
            print(f"  ➔ Parsed Firmware Version: {version_str}")

        time.sleep(0.5)

        # 3. Read EQ
        # AA 07 00 00 0F 01 03 00 00
        eq_req = bytes([0xAA, 0x07, 0x00, 0x00, 0x0F, 0x01, 0x03, 0x00, 0x00])
        print_hex("\n[TX] EQ Read", eq_req)
        s.send(eq_req)
        
        resp = s.recv(1024)
        print_hex("[RX] EQ Read", resp)
        parsed = parse_response(resp)
        eq_names = {0: "Original/Balanced", 1: "Bass Boost", 2: "Clear Vocals"}
        if parsed and parsed["group"] == 0x0F:
            val = parsed["payload"][3] if len(parsed["payload"]) > 3 else -1
            print(f"  ➔ Current EQ Preset: {eq_names.get(val, f'Unknown ({val})')}")

        time.sleep(0.5)

        # 4. Write EQ (Bass Boost)
        # AA 08 00 00 06 04 04 01 00 01
        eq_write = bytes([0xAA, 0x08, 0x00, 0x00, 0x06, 0x04, 0x04, 0x01, 0x00, 0x01])
        print_hex("\n[TX] EQ Write", eq_write)
        s.send(eq_write)
        
        # We might receive a notification first (group 04) followed by the write Ack (group 06)
        # Let's read up to 2 packets to capture both!
        for i in range(2):
            resp = s.recv(1024)
            print_hex(f"[RX] EQ Write resp {i+1}", resp)
            parsed = parse_response(resp)
            if parsed:
                if parsed["group"] == 0x04:
                    val = parsed["payload"][2] if len(parsed["payload"]) > 2 else -1
                    print(f"  ➔ Notification: EQ Mode changed to: {eq_names.get(val, f'Unknown ({val})')}")
                elif parsed["group"] == 0x06:
                    print("  ➔ Write Ack confirmed successfully!")

    except Exception as e:
        print(f"[-] Comm error: {e}")
    finally:
        s.close()
        print("\n[*] Socket closed.")

if __name__ == "__main__":
    main()
