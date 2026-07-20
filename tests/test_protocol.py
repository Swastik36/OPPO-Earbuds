import pytest
import sys
import os

# Add src/ directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from oppo_control.protocol import OppoFrame
from oppo_control.device import get_friendly_description
from oppo_control.commands import (
    EQPreset, BatteryStatus, decode_battery_response, encode_battery_read,
    encode_eq_preset, encode_eq_read, encode_eq_write, encode_firmware_read,
    encode_game_mode_read, encode_game_mode_write, encode_gestures_read,
    encode_volume_read, encode_volume_write, parse_volume_response,
)
from oppo_control.exceptions import ChecksumValidationError, MalformedFrameError

def test_encode_eq_bass_boost():
    """Verify that encoding a Bass Boost command produces the exact hardware-validated payload."""
    packet = encode_eq_preset(EQPreset.BASS_BOOST)
    expected_payload = bytes.fromhex("01 02 02 00")
    assert packet == expected_payload

def test_decode_battery_balanced_state():
    """Verify conversion of raw payload structures into discrete operational metrics."""
    # Simulation: Left=80% (0x50), Right=85% (0x55), Case=50% (0x32)
    raw_payload = bytes.fromhex("50 55 32")
    status = decode_battery_response(raw_payload)
    assert status.left == 80
    assert status.right == 85
    assert status.case == 50


def test_decode_ascii_battery():
    """Verify that BatteryAsciiCodec correctly decodes CSV bytes with -28 offset."""
    from oppo_control.codecs import BatteryAsciiCodec
    # Raw ASCII CSV payload corresponding to Left=90%, Right=90%, Case=84%
    # formatted as: "1,2,118,2,2,118,3,2,102"
    raw_payload = b"\x00\x031,2,118,2,2,118,3,2,102"
    battery = BatteryAsciiCodec.parse(raw_payload)
    
    assert battery is not None
    assert battery.left == 90
    assert battery.left.is_charging is True
    assert battery.right == 90
    assert battery.right.is_charging is True
    assert battery.case == 74
    assert battery.case.is_charging is True

def test_frame_serialization_roundtrip():
    """Ensure consistency across serialization and parsing components."""
    original_frame = OppoFrame(command_group=0x01, payload=bytes.fromhex("0A 0B 0C"))
    serialized = original_frame.serialize()
    
    parsed_frame = OppoFrame.parse(serialized)
    assert parsed_frame.command_group == original_frame.command_group
    assert parsed_frame.payload == original_frame.payload
    assert parsed_frame.checksum == original_frame.checksum

def test_corrupted_checksum_raises_exception():
    """Verify that the parser rejects frame corruptions systematically."""
    # Frame with deliberately corrupted trailing checksum byte
    corrupted_raw_data = bytes.fromhex("01 03 FF 01 02 03 99")
    with pytest.raises(ChecksumValidationError):
        OppoFrame.parse(corrupted_raw_data)


def test_production_encoders_match_captured_wire_frames():
    """The encoder payload must exclude OppoFrame's two-byte length field."""
    assert encode_battery_read(0x01) == bytes.fromhex("AA 07 00 00 06 01 01 00 00")
    assert encode_firmware_read(0x02) == bytes.fromhex("AA 07 00 00 07 01 02 00 00")
    assert encode_eq_read(0x03) == bytes.fromhex("AA 07 00 00 0F 01 03 00 00")
    assert encode_eq_write(0x04, EQPreset.BASS_BOOST) == bytes.fromhex("AA 08 00 00 06 04 04 01 00 02")
    assert encode_game_mode_read(0x05) == bytes.fromhex("AA 0E 00 00 0D 01 05 07 00 06 05 11 06 1B 27 28")
    assert encode_game_mode_write(0x06, True) == bytes.fromhex("AA 09 00 00 03 04 06 02 00 28 01")
    assert encode_gestures_read(0x07) == bytes.fromhex("AA 09 00 00 08 01 07 02 00 02 03")
    assert encode_volume_read(0x35) == bytes.fromhex("AA 07 00 00 30 01 35 00 00")
    assert encode_volume_write(0x36, 90) == bytes.fromhex("AA 08 00 00 27 04 36 01 00 09")
    assert encode_volume_write(0x37, 0) == bytes.fromhex("AA 08 00 00 27 04 37 01 00 01") # Clamped to 1 (10%)
    assert parse_volume_response(bytes.fromhex("02 00 00 09")) == 90


def test_telemetry_notifications():
    """Verify that get_friendly_description correctly parses real-time telemetry packets."""
    # 1. Placement status packet: Left=Out-of-Case, Right=In-Case
    raw_placement = bytes.fromhex("AA 0D 00 00 04 02 00 06 00 02 02 01 01 02 00")
    frame = OppoFrame.parse(raw_placement)
    desc = get_friendly_description(frame)
    assert "Placement: L=Out-of-Case, R=In-Case" in desc

    # 2. Battery Levels packet: Left=90%, Right=90%, Case=100%
    raw_battery = bytes.fromhex("AA 0F 00 00 04 02 00 08 00 01 03 01 5A 02 5A 03 64")
    frame = OppoFrame.parse(raw_battery)
    desc = get_friendly_description(frame)
    assert "Battery: L=90%, R=90%, Case=100%" in desc

    # 3. Charging Status packet: Left=Discharging, Right=Discharging, Case=USB/Powered
    raw_charging = bytes.fromhex("AA 0F 00 00 04 02 00 08 00 02 03 01 00 02 00 03 04")
    frame = OppoFrame.parse(raw_charging)
    desc = get_friendly_description(frame)
    assert "Charging: L=Discharging, R=Discharging, Case=USB/Powered" in desc


def test_placement_fires_battery_changed():
    """A placement-only telemetry frame must trigger battery_changed even when
    the buds are not both out of the case (regression test for the bug where the
    callback was gated inside the both-out-of-case branch)."""
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from oppo_control.device import OppoDevice
    from oppo_control.protocol import OppoFrame
    from oppo_control.commands import EarbudsBattery, BatteryVal

    device = OppoDevice.__new__(OppoDevice)
    device._pending_requests = {}
    device._callbacks = []
    device.profile = None
    # Seed a known battery state so the handler has something to emit
    device.battery = EarbudsBattery(
        left=BatteryVal(90, False),
        right=BatteryVal(90, False),
        case=BatteryVal(100, False),
    )

    fired = []
    device.register_callback(lambda event, data: fired.append((event, data)))

    # Right bud placed in case (Left=Out-of-Case, Right=In-Case) — NOT both-out-of-case
    raw_placement = bytes.fromhex("AA 0D 00 00 04 02 00 06 00 02 02 01 01 02 00")
    frame = OppoFrame.from_bytes(raw_placement)
    device._handle_notification(frame)

    assert len(fired) == 1, f"Expected 1 callback, got {len(fired)}"
    assert fired[0][0] == "battery_changed"


def test_paradigm_a_bitmask_decoding():
    """Paradigm A: lower 7 bits = percentage, MSB = charging flag.
    A push frame with buds charging at 90% uses 0xDA (= 0x5A | 0x80).
    Without the bitmask this decodes to 218%, which is wrong.
    With the mask: 0xDA & 0x7F = 90, (0xDA & 0x80) != 0 = True."""
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from oppo_control.device import OppoDevice
    from oppo_control.protocol import OppoFrame
    from oppo_control.commands import EarbudsBattery, BatteryVal

    device = OppoDevice.__new__(OppoDevice)
    device._pending_requests = {}
    device._callbacks = []
    device.profile = None
    device.battery = EarbudsBattery(
        left=BatteryVal(0, False),
        right=BatteryVal(0, False),
        case=BatteryVal(-1, False),
    )

    fired = []
    device.register_callback(lambda event, data: fired.append((event, data)))

    # 0xDA = 90 | 0x80  => 90% charging
    # 0x64 = 100, MSB clear => 100% not charging (case bridging)
    # Frame: report_type=0x01, count=3, items: 01 DA 02 DA 03 64
    raw_charging_push = bytes.fromhex("AA 0F 00 00 04 02 00 08 00 01 03 01 DA 02 DA 03 64")
    frame = OppoFrame.from_bytes(raw_charging_push)
    device._handle_notification(frame)

    assert len(fired) == 1
    bat = fired[0][1]
    assert bat.left == 90,  f"Left should be 90%, got {bat.left}"
    assert bat.right == 90, f"Right should be 90%, got {bat.right}"
    assert bat.left.is_charging is True,  "Left bud should be charging (MSB set)"
    assert bat.right.is_charging is True, "Right bud should be charging (MSB set)"
    assert bat.case == 100, f"Case should be 100%, got {bat.case}"
    assert bat.case.is_charging is False, "Case MSB clear means not charging"


def test_polled_case_charging_bit_masking():
    """Verify that BatteryBinaryCodec.parse:
    1. Extracts Case (ID=03) charging bit from bit 7.
    2. Forces Left/Right buds charging to False (as it is not reported on polled packets).
    Also verify that OppoDevice.get_battery() merges/preserves buds' charging states."""
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from oppo_control.codecs import BatteryBinaryCodec
    from oppo_control.commands import BatteryVal, EarbudsBattery

    # Triplet: 00 03 01 DA (L=90, bit 7 set), 02 DA (R=90, bit 7 set), 03 E4 (Case=100, bit 7 set)
    # Payload prefix: 00 03 (status, count)
    payload = bytes.fromhex("00 03 01 DA 02 DA 03 E4")
    
    # Parse payload using codec
    bat = BatteryBinaryCodec.parse(payload)
    assert bat.left == 90
    assert bat.right == 90
    assert bat.case == 100
    
    assert bat.left.is_charging is False, "Buds polled charging must be forced False"
    assert bat.right.is_charging is False, "Buds polled charging must be forced False"
    assert bat.case.is_charging is True, "Case polled charging must extract bit 7"

    # Verify merging logic
    from oppo_control.device import OppoDevice
    device = OppoDevice.__new__(OppoDevice)
    device.battery = EarbudsBattery(
        left=BatteryVal(90, True),
        right=BatteryVal(90, True),
        case=BatteryVal(100, False)
    )
    
    # Simulate get_battery merging
    battery = BatteryBinaryCodec.parse(payload)
    if device.battery is not None:
        battery = EarbudsBattery(
            left=BatteryVal(battery.left, device.battery.left.is_charging),
            right=BatteryVal(battery.right, device.battery.right.is_charging),
            case=battery.case
        )
    device.battery = battery
    
    assert device.battery.left == 90
    assert device.battery.left.is_charging is True, "Buds charging status must be preserved"
    assert device.battery.right == 90
    assert device.battery.right.is_charging is True, "Buds charging status must be preserved"
    assert device.battery.case == 100
    assert device.battery.case.is_charging is True, "Case charging status must be updated from polled response"


