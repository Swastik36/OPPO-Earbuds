import asyncio
import time
import logging
from typing import Callable, List, Dict, Optional

from .transport import OppoRFCOMMTransport
from .protocol import OppoFrame
from .devices import DeviceProfile, detect_profile_by_bytes, EncoBuds3ProProfile
from .commands import (
    EQPreset, EarbudsBattery, BatteryVal, TouchGesture,
    encode_battery_read,
    encode_eq_read, encode_eq_write,
    encode_game_mode_read, encode_game_mode_write,
    encode_firmware_read,
    encode_gestures_read, encode_gestures_write,
    encode_find_device,
    encode_volume_read, encode_volume_write
)
from .codecs import EQCodec, GameModeCodec, GestureCodec, FindDeviceCodec, VolumeCodec

logger = logging.getLogger("oppo_control.device")

def get_friendly_description(frame: OppoFrame, profile: Optional[DeviceProfile] = None) -> str:
    cmd_val = (frame.cmd_id << 8) | frame.group
    
    if cmd_val == 0x0100:
        return "Initialize Connection Link"
    elif cmd_val == 0x0105:
        return "Query Battery Telemetry (Legacy ASCII)"
    elif cmd_val == 0x8105:
        desc = "Battery Response (Legacy ASCII)"
        from .codecs import BatteryAsciiCodec
        bat = BatteryAsciiCodec.parse(frame.payload)
        if bat:
            desc += f" (Left: {bat.left}%, Right: {bat.right}%, Case: {bat.case}%)"
        return desc
    elif cmd_val == 0x0106:
        return "Query Battery Telemetry"
    elif cmd_val == 0x8106:
        desc = "Battery Response"
        from .codecs import BatteryBinaryCodec
        bat = BatteryBinaryCodec.parse(frame.payload)
        if bat:
            desc += f" (Left: {bat.left}%, Right: {bat.right}%, Case: {bat.case}%)"
        return desc
    elif cmd_val == 0x0107:
        return "Query Firmware Version"
    elif cmd_val == 0x8107:
        desc = "Firmware Response"
        if profile:
            fw = profile.firmware_codec.parse(frame.payload)
            if fw:
                desc += f" (Version: {fw})"
        return desc
    elif cmd_val == 0x0108:
        return "Query Touch Gestures Matrix"
    elif cmd_val == 0x8108:
        return f"Touch Gestures Matrix Response ({len(frame.payload) // 4} records)"
    elif cmd_val == 0x010F:
        return "Query EQ Preset Status"
    elif cmd_val == 0x810F:
        desc = "EQ Status Response"
        try:
            eq = EQCodec.parse_response(frame.payload)
            if eq:
                desc += f" (Preset: {eq.name})"
        except Exception:
            pass
        return desc
    elif cmd_val == 0x0403:
        desc = "Write Feature Switch"
        if len(frame.payload) >= 2:
            feat_id = frame.payload[0]
            status = "ON" if frame.payload[1] == 1 else "OFF"
            desc += f" (Feature: {feat_id} ➔ {status})"
        return desc
    elif cmd_val == 0x8403:
        return "Write Feature Switch Ack"
    elif cmd_val == 0x0406:
        desc = "Write EQ Preset"
        if len(frame.payload) >= 3:
            desc += f" (Preset Index: {frame.payload[2]})"
        return desc
    elif cmd_val == 0x8406:
        return "Write EQ Preset Ack"
    elif cmd_val == 0x0400:
        desc = "Write Find Device Ring Alert"
        if len(frame.payload) >= 1:
            state = "START" if frame.payload[0] == 1 else "STOP"
            desc += f" (State: {state})"
        return desc
    elif cmd_val == 0x8400:
        return "Write Find Device Ack"
    elif cmd_val == 0x0130:
        return "Query Prompt Volume"
    elif cmd_val == 0x8130:
        desc = "Prompt Volume Response"
        if len(frame.payload) >= 1:
            desc += f" (Volume: {int(frame.payload[-1])}%)"
        return desc
    elif cmd_val == 0x0427:
        desc = "Write Prompt Volume"
        if len(frame.payload) >= 1:
            desc += f" (Volume: {int(frame.payload[-1])}%)"
        return desc
    elif cmd_val == 0x8427:
        return "Write Prompt Volume Ack"
    elif cmd_val == 0x0503:
        desc = "Push: Game Mode Changed"
        if b"\x28\x01" in frame.payload:
            desc += " (ON)"
        elif b"\x28\x00" in frame.payload:
            desc += " (OFF)"
        return desc
    elif cmd_val == 0x0504:
        desc = "Push: EQ Preset Changed"
        if len(frame.payload) >= 3:
            desc += f" (Preset Index: {frame.payload[2]})"
        return desc
    elif cmd_val == 0x0204:
        desc = "Telemetry Notification"
        payload = frame.payload
        if len(payload) >= 2:
            report_type = payload[0]
            count = payload[1]
            items = {}
            offset = 2
            for _ in range(count):
                if offset + 2 <= len(payload):
                    item_id = payload[offset]
                    item_val = payload[offset+1]
                    items[item_id] = item_val
                    offset += 2
            if report_type == 0x01:
                # Paradigm A: lower 7 bits = percentage, MSB = charging flag
                def _fmt(raw):
                    if raw == -1:
                        return "?%"
                    pct = raw & 0x7F
                    chg = " ⚡" if (raw & 0x80) else ""
                    return f"{pct}%{chg}"
                l_val = items.get(1, -1)
                r_val = items.get(2, -1)
                c_val = items.get(3, -1)
                desc += f" (Battery: L={_fmt(l_val)}, R={_fmt(r_val)}, Case={_fmt(c_val)})"
            elif report_type == 0x02:
                if count == 3:
                    val_names = {0: "Discharging", 1: "Charging", 2: "Full", 3: "Error", 4: "USB/Powered"}
                    l_chg = val_names.get(items.get(1, -1), "Unknown")
                    r_chg = val_names.get(items.get(2, -1), "Unknown")
                    c_chg = val_names.get(items.get(3, -1), "Unknown")
                    desc += f" (Charging: L={l_chg}, R={r_chg}, Case={c_chg})"
                elif count == 2:
                    place_names = {0: "In-Case", 1: "Out-of-Case"}
                    l_place = place_names.get(items.get(1, -1), "Unknown")
                    r_place = place_names.get(items.get(2, -1), "Unknown")
                    desc += f" (Placement: L={l_place}, R={r_place})"
        return desc
    return f"Unknown Command (0x{cmd_val:04X})"


class OppoDevice:
    def __init__(self, mac_address: str = "60:55:56:22:49:A0", port: int = 15, trace_mode: bool = False, record_file: Optional[str] = None):
        self.mac_address = mac_address
        self.port = port
        self._transport = OppoRFCOMMTransport(mac_address, port)
        self._transport.trace_mode = trace_mode
        self._next_seq = 1
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._callbacks: List[Callable[[str, any], None]] = []
        self.profile: Optional[DeviceProfile] = None
        self.battery: Optional[EarbudsBattery] = None
        
        self.record_fh = None
        if record_file:
            self.record_fh = open(record_file, "a", encoding="utf-8")
            self.record_fh.write(f"\n--- SESSION RECORD START: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            self.record_fh.flush()
            self._transport.record_callback = self._record_frame_to_file

    def _get_next_seq(self) -> int:
        seq = self._next_seq
        self._next_seq = (self._next_seq + 1) if self._next_seq < 254 else 1
        return seq

    def register_callback(self, callback: Callable[[str, any], None]):
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str, any], None]):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _trigger_callbacks(self, event_type: str, data: any):
        for cb in self._callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

    async def connect(self):
        await self._transport.connect(self._handle_frame)

    async def disconnect(self):
        await self._transport.disconnect()
        if self.record_fh:
            self.record_fh.write(f"--- SESSION RECORD END: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            self.record_fh.close()
            self.record_fh = None

    @property
    def is_connected(self) -> bool:
        return self._transport.is_connected

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    def _record_frame_to_file(self, direction: str, raw_data: bytes):
        if not self.record_fh:
            return
        ts = time.time()
        desc = "Unparsed Bytes"
        try:
            frame = OppoFrame.from_bytes(raw_data)
            desc = get_friendly_description(frame, self.profile)
        except Exception:
            pass
        self.record_fh.write(f"{ts:.6f} | {direction} | {raw_data.hex().upper()} | {desc}\n")
        self.record_fh.flush()

    async def _send_request(self, req_bytes: bytes, seq_id: int) -> OppoFrame:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_requests[seq_id] = fut
        
        try:
            await self._transport.send(req_bytes)
            resp_frame = await asyncio.wait_for(fut, timeout=2.0)
            return resp_frame
        finally:
            self._pending_requests.pop(seq_id, None)

    def _handle_frame(self, frame: OppoFrame):
        if frame.seq_id == 0 or frame.seq_id == 255:
            self._handle_notification(frame)
            return

        fut = self._pending_requests.get(frame.seq_id)
        if fut and not fut.done():
            fut.set_result(frame)

    def _handle_notification(self, frame: OppoFrame):
        logger.info(f"Unsolicited notification received: {frame}")
        
        # EQ Status Notification
        if frame.group == 0x04 and frame.cmd_id == 0x05:
            if frame.payload.startswith(b"\x01\x00"):
                val = frame.payload[2] if len(frame.payload) > 2 else -1
                preset = EQPreset.from_val(val)
                logger.info(f"Notification: EQ Preset updated to {preset.name}")
                self._trigger_callbacks("eq_changed", preset)
                
        # Game Mode Notification
        elif frame.group == 0x03 and frame.cmd_id == 0x05:
            if b"\x28\x01" in frame.payload:
                logger.info("Notification: Game Mode turned ON")
                self._trigger_callbacks("game_mode_changed", True)
            elif b"\x28\x00" in frame.payload:
                logger.info("Notification: Game Mode turned OFF")
                self._trigger_callbacks("game_mode_changed", False)
        
        # Telemetry updates (Real-time Battery and Placement)
        elif frame.group == 0x04 and frame.cmd_id == 0x02:
            payload = frame.payload
            if len(payload) >= 2:
                report_type = payload[0]
                count = payload[1]
                
                if self.battery is None:
                    self.battery = EarbudsBattery(
                        left=BatteryVal(0, False),
                        right=BatteryVal(0, False),
                        case=BatteryVal(-1, False)
                    )
                
                items = {}
                offset = 2
                for _ in range(count):
                    if offset + 2 <= len(payload):
                        item_id = payload[offset]
                        item_val = payload[offset+1]
                        items[item_id] = item_val
                        offset += 2
                
                if report_type == 0x01:
                    # Paradigm A (ETEK1): lower 7 bits = percentage, MSB = charging flag
                    # e.g. 0x5A (90, not charging), 0xDA (90 | 0x80, charging)
                    def _decode(raw, fallback):
                        if raw is None:
                            return int(fallback), fallback.is_charging
                        return raw & 0x7F, (raw & 0x80) != 0

                    l_pct, l_chg = _decode(items.get(1), self.battery.left)
                    r_pct, r_chg = _decode(items.get(2), self.battery.right)
                    c_raw = items.get(3)
                    c_pct, c_chg = _decode(c_raw, self.battery.case)

                    # Case reports 0x00 when both buds are out and it can't bridge;
                    # treat that as disconnected rather than 0 %.
                    if c_raw is not None and (c_raw & 0x7F) == 0:
                        c_pct = -1

                    self.battery = EarbudsBattery(
                        left=BatteryVal(l_pct, l_chg),
                        right=BatteryVal(r_pct, r_chg),
                        case=BatteryVal(c_pct, c_chg),
                    )
                    logger.info(f"Telemetry: Battery Levels updated (Paradigm A): {self.battery}")
                    self._trigger_callbacks("battery_changed", self.battery)

                elif report_type == 0x02:
                    if count == 3:
                        # Supplementary charging-state frame (raw state bytes, not bitmask).
                        # Use this to override charging flags when present, but don't touch
                        # percentage values which came from report_type==0x01.
                        l_chg = items.get(1, 0) == 1
                        r_chg = items.get(2, 0) == 1
                        c_chg = items.get(3, 0) in [1, 4]

                        self.battery = EarbudsBattery(
                            left=BatteryVal(int(self.battery.left), l_chg),
                            right=BatteryVal(int(self.battery.right), r_chg),
                            case=BatteryVal(int(self.battery.case), c_chg),
                        )
                        logger.info(f"Telemetry: Charging States override: {self.battery}")
                        self._trigger_callbacks("battery_changed", self.battery)
                    elif count == 2:
                        # Placement / Wearing status update
                        # 0x00 = In-Case, 0x01 = Out-of-Case
                        l_in_case = items.get(1, 1) == 0
                        r_in_case = items.get(2, 1) == 0

                        if not l_in_case and not r_in_case:
                            # Both out of case: case can no longer bridge battery info
                            self.battery = EarbudsBattery(
                                left=self.battery.left,
                                right=self.battery.right,
                                case=BatteryVal(-1, False),
                            )
                            logger.info("Telemetry: Both buds out of case, Case Disconnected")

                        # Always notify UI on any placement change
                        logger.info(f"Telemetry: Placement updated L_in_case={l_in_case} R_in_case={r_in_case}")
                        self._trigger_callbacks("battery_changed", self.battery)
        else:
            logger.info(f"Unhandled notification received: group=0x{frame.group:02X} cmd=0x{frame.cmd_id:02X} payload={frame.payload.hex().upper()}")


    # --- Public API methods ---

    async def get_battery(self) -> EarbudsBattery:
        seq = self._get_next_seq()
        req = encode_battery_read(seq)
        resp = await self._send_request(req, seq)
        
        if self.profile is None:
            self.profile = detect_profile_by_bytes(resp.payload, self.mac_address)
            logger.info(f"Auto-detected capabilities profile: {self.profile.name}")
            
        battery = self.profile.battery_codec.parse(resp.payload)
        if battery is None:
            raise ValueError("Failed to parse battery response using profile battery_codec")
        if self.battery is not None:
            # Merge charging states for buds since polled binary queries do not set bit 7 on buds
            battery = EarbudsBattery(
                left=BatteryVal(battery.left, self.battery.left.is_charging),
                right=BatteryVal(battery.right, self.battery.right.is_charging),
                case=battery.case
            )
        self.battery = battery
        return battery

    async def get_battery_status(self) -> EarbudsBattery:
        return await self.get_battery()

    async def get_firmware(self) -> str:
        seq = self._get_next_seq()
        req = encode_firmware_read(seq)
        resp = await self._send_request(req, seq)
        
        if self.profile is None:
            try:
                await self.get_battery()
            except Exception:
                self.profile = EncoBuds3ProProfile
                
        version = self.profile.firmware_codec.parse(resp.payload)
        if version is None:
            from .codecs import FirmwareAsciiCodec, FirmwareBinaryCodec
            alt_codec = FirmwareAsciiCodec if self.profile.firmware_codec == FirmwareBinaryCodec else FirmwareBinaryCodec
            version = alt_codec.parse(resp.payload)
            
        if version is None:
            raise ValueError("Failed to parse firmware version response")
        return version

    async def get_eq(self) -> EQPreset:
        seq = self._get_next_seq()
        req = encode_eq_read(seq)
        resp = await self._send_request(req, seq)
        preset = EQCodec.parse_response(resp.payload)
        if preset is None:
            raise ValueError("Failed to parse EQ response")
        return preset

    async def set_eq(self, preset: EQPreset):
        seq = self._get_next_seq()
        req = encode_eq_write(seq, preset)
        resp = await self._send_request(req, seq)
        if resp.group != 0x06 or resp.cmd_id != 0x84:
            raise ValueError("Failed to write EQ Preset (invalid response frame)")

    async def set_equalizer(self, preset: EQPreset):
        await self.set_eq(preset)

    async def get_game_mode(self) -> bool:
        seq = self._get_next_seq()
        req = encode_game_mode_read(seq)
        resp = await self._send_request(req, seq)
        status = GameModeCodec.parse_response(resp.payload)
        if status is None:
            raise ValueError("Failed to parse Game Mode response")
        return status

    async def set_game_mode(self, enable: bool):
        seq = self._get_next_seq()
        req = encode_game_mode_write(seq, enable)
        resp = await self._send_request(req, seq)
        if resp.group != 0x03 or resp.cmd_id != 0x84:
            raise ValueError("Failed to write Game Mode (invalid response frame)")

    async def get_gestures(self) -> List[TouchGesture]:
        seq = self._get_next_seq()
        req = encode_gestures_read(seq)
        resp = await self._send_request(req, seq)
        gestures = GestureCodec.parse_response(resp.payload)
        if gestures is None:
            raise ValueError("Failed to parse Touch Gestures response")
        return gestures

    async def set_gestures(self, gestures: List[TouchGesture]):
        seq = self._get_next_seq()
        req = encode_gestures_write(seq, gestures)
        resp = await self._send_request(req, seq)
        if resp.group != 0x01 or resp.cmd_id != 0x84:
            raise ValueError("Failed to write Touch Gestures (invalid response frame)")

    async def find_device(self, start: bool):
        seq = self._get_next_seq()
        req = encode_find_device(seq, start)
        resp = await self._send_request(req, seq)
        if resp.group != 0x00 or resp.cmd_id != 0x84:
            raise ValueError("Failed to send Find Device command (invalid response frame)")

    async def get_volume(self) -> int:
        seq = self._get_next_seq()
        req = encode_volume_read(seq)
        resp = await self._send_request(req, seq)
        vol = VolumeCodec.parse_response(resp.payload)
        if vol is None:
            raise ValueError("Failed to parse Alert Volume response")
        return vol

    async def set_volume(self, volume: int):
        seq = self._get_next_seq()
        req = encode_volume_write(seq, volume)
        resp = await self._send_request(req, seq)
        if resp.group != 0x27 or resp.cmd_id != 0x84:
            raise ValueError("Failed to set Alert Volume (invalid response frame)")

    async def set_anc_mode(self, mode: str):
        logger.warning(f"ANC mode set to '{mode}' requested, but standard OPPO Enco Buds3 Pro hardware does not support ANC.")
        return True
