import struct
from typing import List, Optional
from .commands import EQPreset, EarbudsBattery, BatteryVal, TouchGesture

# --- Battery Codecs ---

class BatteryAsciiCodec:
    @staticmethod
    def parse(payload: bytes) -> Optional[EarbudsBattery]:
        if len(payload) <= 2:
            return None
        try:
            csv_str = payload[2:].decode("ascii", errors="ignore")
            parts = csv_str.split(",")
            left, right, case = None, None, None
            
            for i in range(0, len(parts) - 2, 3):
                device_id = parts[i]
                charging_state = parts[i + 1]
                try:
                    battery_val = int(parts[i + 2])
                except ValueError:
                    continue
                
                charging = charging_state == "2"
                pct = max(0, min(100, battery_val - 28))
                val = BatteryVal(pct, charging)
                
                if device_id == "1":
                    left = val
                elif device_id == "2":
                    right = val
                elif device_id == "3":
                    case = val
            
            left = left or BatteryVal(0, False)
            right = right or BatteryVal(0, False)
            case = case or BatteryVal(-1, False)
            return EarbudsBattery(left, right, case)
        except Exception:
            pass
        return None


class BatteryBinaryCodec:
    @staticmethod
    def parse(payload: bytes) -> Optional[EarbudsBattery]:
        if len(payload) < 2:
            return None
        try:
            count = payload[1]
            left, right, case = None, None, None
            
            for i in range(count):
                offset = 2 + i * 2
                if offset + 1 >= len(payload):
                    break
                battery_id = payload[offset]
                info = payload[offset + 1]
                
                level = info & 0x7F
                if battery_id in (1, 2):
                    charging = False
                else:
                    charging = (info & 0x80) != 0
                val = BatteryVal(level, charging)
                
                if battery_id == 1:
                    left = val
                elif battery_id == 2:
                    right = val
                elif battery_id == 3:
                    case = val
            
            left = left or BatteryVal(0, False)
            right = right or BatteryVal(0, False)
            case = case or BatteryVal(0, False)
            return EarbudsBattery(left, right, case)
        except Exception:
            pass
        return None


# --- Firmware Codecs ---

class FirmwareBinaryCodec:
    @staticmethod
    def parse(payload: bytes) -> Optional[str]:
        if len(payload) >= 6:
            v_bytes = payload[1:6]
            return ".".join(str(b) for b in v_bytes)
        return None


class FirmwareAsciiCodec:
    @staticmethod
    def parse(payload: bytes) -> Optional[str]:
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


# --- Equalizer Codecs ---

class EQCodec:
    @staticmethod
    def encode_read(seq_id: int) -> bytes:
        from .protocol import OppoFrame
        # Confirmed from btsnoop: AA0700000F01XXXX — no extra payload bytes
        return OppoFrame(group=0x0F, cmd_id=0x01, seq_id=seq_id, payload=b'').to_bytes()

    @staticmethod
    def encode_write(seq_id: int, preset: EQPreset) -> bytes:
        from .protocol import OppoFrame
        # Confirmed wire format: ... [seq] 01 00 [preset].  01 00 is the
        # payload-length field added by OppoFrame, so only preset is payload.
        payload = bytes([int(preset)])
        return OppoFrame(group=0x06, cmd_id=0x04, seq_id=seq_id, payload=payload).to_bytes()

    @staticmethod
    def parse_response(payload: bytes) -> Optional[EQPreset]:
        # Confirmed from btsnoop pkt#1414: response payload=02 00 00 00
        # byte[0]=length, byte[1]=0x00, byte[2]=preset_val
        if len(payload) >= 3:
            return EQPreset.from_val(payload[2])
        if len(payload) >= 2 and payload[0] in (0x00, 0x02):
            return EQPreset.from_val(payload[1])
        return None


# --- Game Mode Codecs ---

class GameModeCodec:
    @staticmethod
    def encode_read(seq_id: int) -> bytes:
        from .protocol import OppoFrame
        # Confirmed from btsnoop pkt#1496: AA0E00000D01XX0700060511061B2728
        # 07 00 in the capture is the payload length.  The payload is the
        # seven feature IDs below.
        payload = bytes([0x06, 0x05, 0x11, 0x06, 0x1B, 0x27, 0x28])
        return OppoFrame(group=0x0D, cmd_id=0x01, seq_id=seq_id, payload=payload).to_bytes()

    @staticmethod
    def encode_write(seq_id: int, enable: bool) -> bytes:
        from .protocol import OppoFrame
        val = 1 if enable else 0
        # Confirmed from btsnoop pkt#1483: AA09000003047602002801
        # Wire format: ... [seq] 02 00 28 [val].  02 00 is the payload length.
        payload = bytes([0x28, val])
        return OppoFrame(group=0x03, cmd_id=0x04, seq_id=seq_id, payload=payload).to_bytes()

    @staticmethod
    def parse_response(payload: bytes) -> Optional[bool]:
        # Confirmed from btsnoop pkt#1500 response: ...28 01 (ON) or 28 00 (OFF)
        if b"\x28\x01" in payload:
            return True
        if b"\x28\x00" in payload:
            return False
        return None


# --- Touch Gesture Codecs ---

class GestureCodec:
    @staticmethod
    def encode_read(seq_id: int) -> bytes:
        from .protocol import OppoFrame
        return OppoFrame(group=0x08, cmd_id=0x01, seq_id=seq_id, payload=bytes([0x02, 0x03])).to_bytes()

    @staticmethod
    def encode_write(seq_id: int, gestures: List[TouchGesture]) -> bytes:
        from .protocol import OppoFrame
        payload = bytearray([len(gestures)])
        for g in gestures:
            payload.extend([g.earbud_id, g.action_type, g.trigger_id, g.function_id])
        return OppoFrame(group=0x01, cmd_id=0x04, seq_id=seq_id, payload=bytes(payload)).to_bytes()

    @staticmethod
    def parse_response(payload: bytes) -> Optional[List[TouchGesture]]:
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


# --- Find Device Codecs ---

class FindDeviceCodec:
    @staticmethod
    def encode_write(seq_id: int, start: bool) -> bytes:
        from .protocol import OppoFrame
        val = 0x01 if start else 0x00
        return OppoFrame(group=0x00, cmd_id=0x04, seq_id=seq_id, payload=bytes([val])).to_bytes()


# --- Prompt Volume Codecs ---

class VolumeCodec:
    @staticmethod
    def encode_read(seq_id: int) -> bytes:
        from .protocol import OppoFrame
        return OppoFrame(group=0x30, cmd_id=0x01, seq_id=seq_id, payload=b'').to_bytes()

    @staticmethod
    def encode_write(seq_id: int, volume: int) -> bytes:
        from .protocol import OppoFrame
        # Scale UI slider value (10-100) down to hardware volume value (1-10)
        hw_vol = max(1, min(10, int(round(volume / 10.0))))
        return OppoFrame(group=0x27, cmd_id=0x04, seq_id=seq_id, payload=bytes([hw_vol])).to_bytes()

    @staticmethod
    def parse_response(payload: bytes) -> Optional[int]:
        if len(payload) >= 1:
            # Scale hardware volume value (0-10) up to UI slider percentage (0-100)
            return int(payload[-1]) * 10
        return None
