#!/usr/bin/env python3
"""
paired_sample.py — extract 0x8105 poll responses and 0x0204 battery push frames
from the same CFA log and pair them by timestamp proximity.

Usage:
    python3 scripts/paired_sample.py captures/<file>.cfa
"""
import struct
import sys
from datetime import datetime, timedelta

EPOCH_OFFSET_US = 0x00E03AB05702B000  # btsnoop epoch → Unix epoch


def parse_btsnoop(path):
    packets = []
    with open(path, "rb") as f:
        hdr = f.read(16)
        if len(hdr) < 16 or not hdr.startswith(b"btsnoop\x00"):
            raise ValueError("Not a btsnoop file")
        idx = 0
        while True:
            pkt_hdr = f.read(24)
            if len(pkt_hdr) < 24:
                break
            orig_len, incl_len, flags, drops, ts_us = struct.unpack(">IIIIq", pkt_hdr)
            data = f.read(incl_len)
            if len(data) < incl_len:
                break
            idx += 1
            try:
                epoch_us = ts_us - EPOCH_OFFSET_US
                ts = datetime(1970, 1, 1) + timedelta(microseconds=epoch_us)
            except Exception:
                ts = None
            direction = "RX" if (flags & 1) else "TX"
            packets.append({"idx": idx, "ts": ts, "dir": direction, "data": data})
    return packets


def extract_rfcomm_payload(data):
    """Return the OPPO frame payload bytes from an HCI ACL packet, or None."""
    offset = 0
    if data and data[0] in [0x01, 0x02, 0x03, 0x04, 0x05]:
        if data[0] != 0x02:
            return None
        offset = 1
    else:
        pass  # treat as ACL

    if len(data) < offset + 8:
        return None
    _, acl_len = struct.unpack("<HH", data[offset:offset + 4])
    offset += 4
    _, cid = struct.unpack("<HH", data[offset:offset + 4])
    offset += 4

    if cid not in [65, 12352]:
        return None

    rfcomm = data[offset:]
    if len(rfcomm) < 3:
        return None
    addr = rfcomm[0]
    control = rfcomm[1]
    len_byte = rfcomm[2]
    dlci = addr >> 2
    if dlci != 30:
        return None

    if len_byte & 1:
        length = len_byte >> 1
        rf_off = 4 if control == 0xff else 3
    else:
        if len(rfcomm) < 4:
            return None
        length = (rfcomm[3] << 7) | (len_byte >> 1)
        rf_off = 5 if control == 0xff else 4

    payload = rfcomm[rf_off:rf_off + length]
    if len(payload) < 7 or payload[0] != 0xAA:
        return None
    return payload


def decode_oppo(payload):
    """Return (group, cmd_id, frame_payload) or None."""
    if len(payload) < 7 or payload[0] != 0xAA:
        return None
    frame_len = payload[1]
    if len(payload) < 2 + frame_len:
        return None
    group   = payload[4]
    cmd_id  = payload[5]
    seq_id  = payload[6]
    pld     = payload[7:2 + frame_len]
    return group, cmd_id, seq_id, pld


def decode_ascii_battery(pld):
    """Parse 0x8105 ASCII CSV payload → dict or None."""
    # payload starts with 2-byte header then ASCII CSV
    if len(pld) < 4:
        return None
    try:
        csv = pld[4:].decode("ascii", errors="ignore").strip()
        parts = csv.split(",")
        if len(parts) < 9:
            return None

        def decode_val(raw):
            v = int(raw)
            return v - 100 if v >= 100 else v   # current established mapping

        l_state = "Charging" if parts[1] == "2" else "Discharging"
        r_state = "Charging" if parts[4] == "2" else "Discharging"
        c_state = "Charging" if parts[7] == "2" else "Discharging"

        return {
            "csv": csv,
            "left_raw": int(parts[2]),  "left_pct": decode_val(parts[2]),  "left_state": l_state,
            "right_raw": int(parts[5]), "right_pct": decode_val(parts[5]), "right_state": r_state,
            "case_raw": int(parts[8]),  "case_pct": decode_val(parts[8]),  "case_state": c_state,
        }
    except Exception:
        return None


def decode_push_battery(pld):
    """Parse group=0x04 cmd=0x02 push battery-level payload → dict or None.

    Wire layout after OPPO header:
      [0:2]  LE uint16 length of the remainder
      [2]    report_type (0x01 = battery levels)
      [3]    count of id/val pairs
      [4+]   (id, value) bytes
    """
    if len(pld) < 4:
        return None
    # Skip 2-byte little-endian length prefix
    body = pld[2:]
    report_type = body[0]
    count = body[1]
    if report_type != 0x01:  # only care about battery-level reports
        return None
    items = {}
    offset = 2
    for _ in range(count):
        if offset + 2 <= len(body):
            items[body[offset]] = body[offset + 1]
            offset += 2
    if 1 not in items:
        return None
    return {
        "left_raw": items.get(1),  "left_pct": items.get(1),
        "right_raw": items.get(2), "right_pct": items.get(2),
        "case_raw": items.get(3),  "case_pct": items.get(3),
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file.cfa>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"[*] Parsing {path} ...")
    packets = parse_btsnoop(path)
    print(f"[+] {len(packets)} raw packets\n")

    polls   = []   # (ts, decoded_dict, raw_hex)
    pushes  = []   # (ts, decoded_dict, raw_hex)

    for pkt in packets:
        payload = extract_rfcomm_payload(pkt["data"])
        if payload is None:
            continue
        r = decode_oppo(payload)
        if r is None:
            continue
        group, cmd_id, seq_id, pld = r
        hex_pld = pld.hex().upper()

        # 0x8105 — polled battery response
        if group == 0x05 and cmd_id == 0x81:
            d = decode_ascii_battery(pld)
            if d:
                polls.append((pkt["ts"], d, hex_pld))

        # 0x0204 — push battery level
        if group == 0x04 and cmd_id == 0x02:
            d = decode_push_battery(pld)
            if d:
                pushes.append((pkt["ts"], d, hex_pld))

    print(f"[+] Found {len(polls)} poll responses (0x8105)")
    print(f"[+] Found {len(pushes)} push battery frames (0x0204 type=01)\n")

    # ── Print all poll frames ──────────────────────────────────────────────
    print("=" * 80)
    print("POLLED BATTERY RESPONSES  (0x8105 — ASCII CSV)")
    print("=" * 80)
    for ts, d, raw in polls:
        ts_str = ts.strftime("%H:%M:%S.%f") if ts else "??"
        print(f"  [{ts_str}]  CSV: {d['csv']}")
        print(f"             Left  raw={d['left_raw']:3d}  decoded={d['left_pct']:3d}%  ({d['left_state']})")
        print(f"             Right raw={d['right_raw']:3d}  decoded={d['right_pct']:3d}%  ({d['right_state']})")
        print(f"             Case  raw={d['case_raw']:3d}  decoded={d['case_pct']:3d}%  ({d['case_state']})")
        print()

    # ── Print all push frames ──────────────────────────────────────────────
    print("=" * 80)
    print("PUSH BATTERY LEVELS  (0x0204 report_type=0x01)")
    print("=" * 80)
    for ts, d, raw in pushes:
        ts_str = ts.strftime("%H:%M:%S.%f") if ts else "??"
        print(f"  [{ts_str}]  hex: {raw}")
        print(f"             Left  raw=0x{d['left_raw']:02X}={d['left_raw']:3d}  direct=%{d['left_pct']}")
        print(f"             Right raw=0x{d['right_raw']:02X}={d['right_raw']:3d}  direct=%{d['right_pct']}")
        print(f"             Case  raw=0x{d['case_raw']:02X}={d['case_raw']:3d}  direct=%{d['case_pct']}")
        print()

    # ── Pair nearest push to each poll ────────────────────────────────────
    if polls and pushes:
        print("=" * 80)
        print("PAIRED COMPARISON  (each poll → nearest push within 5 s)")
        print("=" * 80)
        for (p_ts, p_d, _) in polls:
            if p_ts is None:
                continue
            nearest = min(pushes, key=lambda x: abs((x[0] - p_ts).total_seconds()) if x[0] else 999)
            gap = abs((nearest[0] - p_ts).total_seconds()) if nearest[0] else 999
            if gap > 5:
                print(f"  [{p_ts.strftime('%H:%M:%S.%f')}]  poll: L={p_d['left_pct']}% R={p_d['right_pct']}% C={p_d['case_pct']}%"
                      f"  ← no push within 5 s (nearest {gap:.1f}s away)")
            else:
                push_d = nearest[1]
                print(f"  poll @ {p_ts.strftime('%H:%M:%S.%f')}: L={p_d['left_pct']}% R={p_d['right_pct']}% C={p_d['case_pct']}%"
                      f"  (raw L={p_d['left_raw']} R={p_d['right_raw']} C={p_d['case_raw']})")
                print(f"  push @ {nearest[0].strftime('%H:%M:%S.%f')}: L={push_d['left_pct']}% R={push_d['right_pct']}% C={push_d['case_pct']}%"
                      f"  (raw L=0x{push_d['left_raw']:02X} R=0x{push_d['right_raw']:02X} C=0x{push_d['case_raw']:02X})"
                      f"  Δt={gap:.3f}s")
                l_match = "✓" if p_d["left_pct"] == push_d["left_pct"] else f"✗ MISMATCH ({p_d['left_pct']} vs {push_d['left_pct']})"
                r_match = "✓" if p_d["right_pct"] == push_d["right_pct"] else f"✗ MISMATCH ({p_d['right_pct']} vs {push_d['right_pct']})"
                print(f"  Left: {l_match}   Right: {r_match}")
            print()


if __name__ == "__main__":
    main()
