import sys
import os
from oppo_control.protocol import OppoFrame
from oppo_control.device import get_friendly_description

def main():
    log_file = "tests/test_session.oplog"
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
        
    if not os.path.exists(log_file):
        print(f"[-] Error: Log file '{log_file}' does not exist.")
        sys.exit(1)
        
    print(f"[+] Replaying and parsing log file: {log_file}\n")
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("---"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                ts, direction, raw_hex = parts[0], parts[1], parts[2]
                try:
                    raw_bytes = bytes.fromhex(raw_hex)
                    frame = OppoFrame.from_bytes(raw_bytes)
                    desc = get_friendly_description(frame)
                    print(f"[{ts}] {direction} ➔ {raw_hex} | {desc}")
                except Exception as e:
                    print(f"[{ts}] {direction} ➔ {raw_hex} | Failed to Parse ({e})")

if __name__ == "__main__":
    main()
