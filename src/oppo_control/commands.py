from enum import IntEnum
from dataclasses import dataclass
from typing import List

# EQ Presets Enum compatible with both blueprint and real hardware values
class EQPreset(IntEnum):
    ORIGINAL = 0
    VOCALS = 1
    BASS = 2
    # Blueprint aliases
    BASS_BOOST = 2
    TREBLE_BOOST = 1
    VOCAL = 1

    @classmethod
    def from_val(cls, val: int):
        try:
            return cls(val)
        except ValueError:
            return cls.ORIGINAL


# Custom integer subclass to bridge direct integer usage and nested property calls
class BatteryVal(int):
    def __new__(cls, val: int, is_charging: bool):
        obj = super(BatteryVal, cls).__new__(cls, val)
        obj.is_charging = is_charging
        return obj

    @property
    def percentage(self) -> int:
        return int(self)


@dataclass
class EarbudsBattery:
    left: BatteryVal
    right: BatteryVal
    case: BatteryVal

    def __repr__(self) -> str:
        return (f"EarbudsBattery(Left={int(self.left)}% [Charging={self.left.is_charging}], "
                f"Right={int(self.right)}% [Charging={self.right.is_charging}], "
                f"Case={int(self.case)}% [Charging={self.case.is_charging}])")


@dataclass
class TouchGesture:
    earbud_id: int      # 1 = Left, 2 = Right
    action_type: int    # 1 = Basic, 6 = Custom Swipe/Long-press
    trigger_id: int     # 1 = Single, 2 = Double, 3 = Triple, 4 = Long Press, 5 = Double & Hold, 6 = Slide
    function_id: int    # Assigned function ID

    def __repr__(self) -> str:
        ear = "Left" if self.earbud_id == 1 else "Right"
        triggers = {1: "Single Tap", 2: "Double Tap", 3: "Triple Tap", 4: "Long Press", 5: "Double & Hold", 6: "Slide"}
        trig = triggers.get(self.trigger_id, f"Trig-{self.trigger_id}")
        funcs = {0: "No Action", 1: "Play/Pause", 5: "Prev Track", 6: "Next Track", 0x0B: "Volume-", 0x0C: "Volume+", 0x1C: "Game Mode Toggle", 0x1D: "Game Mode Toggle"}
        func = funcs.get(self.function_id, f"Func-{hex(self.function_id)}")
        return f"TouchGesture({ear} {trig} ➔ {func})"


# Battery Real Queries
def encode_battery_read(seq_id: int) -> bytes:
    from .protocol import OppoFrame
    # Query modern binary battery (group 0x06, cmd 0x01)
    return OppoFrame(group=0x06, cmd_id=0x01, seq_id=seq_id, payload=b'').to_bytes()

def parse_battery_response(payload: bytes) -> EarbudsBattery:
    from .codecs import BatteryAsciiCodec, BatteryBinaryCodec
    if len(payload) > 2 and payload[2] in [0x31, 0x32, 0x33]:
        return BatteryAsciiCodec.parse(payload)
    else:
        return BatteryBinaryCodec.parse(payload)

# EQ Real Queries
def encode_eq_write(seq_id: int, preset: EQPreset) -> bytes:
    from .protocol import OppoFrame
    # Wire format: ... [seq] 01 00 [preset].  01 00 is the payload length.
    payload = bytes([int(preset)])
    return OppoFrame(group=0x06, cmd_id=0x04, seq_id=seq_id, payload=payload).to_bytes()

def encode_eq_read(seq_id: int) -> bytes:
    from .protocol import OppoFrame
    # Confirmed from btsnoop pkt#1409: AA0700000F01XXXX — empty payload
    return OppoFrame(group=0x0F, cmd_id=0x01, seq_id=seq_id, payload=b'').to_bytes()

def parse_eq_response(payload: bytes) -> EQPreset:
    if len(payload) >= 4 and payload.startswith(b"\x02\x00\x00"):
        return EQPreset.from_val(payload[3])
    return None

# Game Mode Real Queries
def encode_game_mode_write(seq_id: int, enable: bool) -> bytes:
    from .protocol import OppoFrame
    val = 1 if enable else 0
    # Wire format: ... [seq] 02 00 28 [value].  02 00 is the payload length.
    payload = bytes([0x28, val])
    return OppoFrame(group=0x03, cmd_id=0x04, seq_id=seq_id, payload=payload).to_bytes()

def encode_game_mode_read(seq_id: int) -> bytes:
    from .protocol import OppoFrame
    # The capture's 07 00 is the payload length; the seven feature IDs follow.
    payload = bytes([0x06, 0x05, 0x11, 0x06, 0x1B, 0x27, 0x28])
    return OppoFrame(group=0x0D, cmd_id=0x01, seq_id=seq_id, payload=payload).to_bytes()

def parse_game_mode_response(payload: bytes) -> bool:
    if b"\x28\x01" in payload:
        return True
    if b"\x28\x00" in payload:
        return False
    return None

# Firmware Real Queries
def encode_firmware_read(seq_id: int) -> bytes:
    from .protocol import OppoFrame
    return OppoFrame(group=0x07, cmd_id=0x01, seq_id=seq_id, payload=b'').to_bytes()

def parse_firmware_response(payload: bytes) -> str:
    if not payload:
        return None
        
    if payload[0] == 0x06:
        if len(payload) >= 8:
            v_bytes = payload[3:8]
            return ".".join(str(b) for b in v_bytes)
    else:
        try:
            fw_bytes = payload[2:]
            if fw_bytes.endswith(b"\x00"):
                fw_bytes = fw_bytes[:-1]
            fw_str = fw_bytes.decode("ascii", errors="ignore").strip()
            parts = fw_str.split(",")
            for i in range(0, len(parts) - 2, 3):
                part_id = parts[i]
                version_type = parts[i + 1]
                version = parts[i + 2]
                if version_type == "2" and part_id in ["1", "2"]:
                    return version
        except Exception:
            pass
            
    return None

# Gestures Real Queries / Writes
def encode_gestures_read(seq_id: int) -> bytes:
    from .protocol import OppoFrame
    # Wire format: ... [seq] 03 00 02 03.  03 00 is the payload length.
    return OppoFrame(group=0x08, cmd_id=0x01, seq_id=seq_id, payload=bytes([0x02, 0x03])).to_bytes()

def parse_gestures_response(payload: bytes) -> List[TouchGesture]:
    if len(payload) < 4:
        return None
    num_records = payload[3]
    records_data = payload[4:]
    if len(records_data) < num_records * 4:
        return None
        
    gestures = []
    for i in range(num_records):
        offset = i * 4
        earbud_id = records_data[offset]
        action_type = records_data[offset + 1]
        trigger_id = records_data[offset + 2]
        function_id = records_data[offset + 3]
        gestures.append(TouchGesture(earbud_id, action_type, trigger_id, function_id))
    return gestures

def encode_gestures_write(seq_id: int, gestures: List[TouchGesture]) -> bytes:
    from .protocol import OppoFrame
    # Format: [count] [earbud_id, action_type, trigger_id, function_id] * count
    payload = bytearray([len(gestures)])
    for g in gestures:
        payload.extend([g.earbud_id, g.action_type, g.trigger_id, g.function_id])
    return OppoFrame(group=0x01, cmd_id=0x04, seq_id=seq_id, payload=bytes(payload)).to_bytes()

# Find Device (Ringing) Queries
def encode_find_device(seq_id: int, start: bool) -> bytes:
    from .protocol import OppoFrame
    val = 0x01 if start else 0x00
    return OppoFrame(group=0x00, cmd_id=0x04, seq_id=seq_id, payload=bytes([val])).to_bytes()

# Prompt Sound Volume Queries
def encode_volume_read(seq_id: int) -> bytes:
    from .protocol import OppoFrame
    return OppoFrame(group=0x30, cmd_id=0x01, seq_id=seq_id, payload=b'').to_bytes()

def encode_volume_write(seq_id: int, volume: int) -> bytes:
    from .protocol import OppoFrame
    hw_vol = max(1, min(10, int(round(volume / 10.0))))
    return OppoFrame(group=0x27, cmd_id=0x04, seq_id=seq_id, payload=bytes([hw_vol])).to_bytes()

def parse_volume_response(payload: bytes) -> int:
    if len(payload) >= 1:
        return int(payload[-1]) * 10
    return 0


# --- Stage 3.5 Blueprint Test Compatibility Layer ---

@dataclass
class BatteryStatus:
    left: int
    right: int
    case: int

def encode_eq_preset(preset: EQPreset) -> bytes:
    val = int(preset)
    return bytes([0x01, 0x02, val, 0x00])

def decode_battery_response(raw_payload: bytes) -> BatteryStatus:
    if len(raw_payload) >= 3:
        return BatteryStatus(left=raw_payload[0], right=raw_payload[1], case=raw_payload[2])
    return BatteryStatus(0, 0, 0)

# Alias for backward compatibility
BatteryState = BatteryVal
