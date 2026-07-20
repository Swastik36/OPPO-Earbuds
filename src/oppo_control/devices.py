from dataclasses import dataclass
from typing import Type, Optional
from .codecs import (
    BatteryAsciiCodec, BatteryBinaryCodec,
    FirmwareAsciiCodec, FirmwareBinaryCodec,
    EQCodec, GameModeCodec, GestureCodec, FindDeviceCodec, VolumeCodec
)

@dataclass
class DeviceProfile:
    name: str
    battery_codec: Type
    firmware_codec: Type
    supports_anc: bool = False
    supports_eq: bool = True
    supports_game_mode: bool = True
    supports_gestures: bool = True
    supports_find: bool = True
    supports_volume: bool = True

# --- Specific Model Profiles ---

EncoBuds3ProProfile = DeviceProfile(
    name="OPPO Enco Buds3 Pro",
    battery_codec=BatteryBinaryCodec,
    firmware_codec=FirmwareBinaryCodec,
    supports_anc=False,  # Verified: standard Buds3 Pro has no active noise cancelling hardware registers
    supports_eq=True,
    supports_game_mode=True,
    supports_gestures=True,
    supports_find=True,
    supports_volume=True
)

OnePlusNordBuds3Profile = DeviceProfile(
    name="OnePlus Nord Buds 3",
    battery_codec=BatteryBinaryCodec,
    firmware_codec=FirmwareAsciiCodec,
    supports_anc=True,
    supports_eq=True,
    supports_game_mode=True,
    supports_gestures=True,
    supports_find=True,
    supports_volume=True
)

RealmeAir7Profile = DeviceProfile(
    name="Realme Air 7",
    battery_codec=BatteryBinaryCodec,
    firmware_codec=FirmwareAsciiCodec,
    supports_anc=True,
    supports_eq=True,
    supports_game_mode=True,
    supports_gestures=True,
    supports_find=True,
    supports_volume=True
)

# Fallback Profiles
DefaultLegacyProfile = DeviceProfile(
    name="Generic OPPO/OnePlus Buds (Legacy)",
    battery_codec=BatteryBinaryCodec,
    firmware_codec=FirmwareAsciiCodec,
    supports_anc=True,
    supports_eq=True,
    supports_game_mode=True,
    supports_gestures=True,
    supports_find=True,
    supports_volume=True
)

DefaultModernProfile = DeviceProfile(
    name="Generic OPPO/OnePlus Buds (Modern)",
    battery_codec=BatteryBinaryCodec,
    firmware_codec=FirmwareBinaryCodec,
    supports_anc=False,
    supports_eq=True,
    supports_game_mode=True,
    supports_gestures=True,
    supports_find=True,
    supports_volume=True
)

def detect_profile_by_bytes(battery_payload: bytes, mac_address: Optional[str] = None) -> DeviceProfile:
    """SNIFF check to auto-detect model profile based on the first battery query response."""
    # 1. Check if legacy ASCII CSV response (starts with ASCII '1', '2', '3')
    # If legacy query was used, the codec must fall back to ASCII
    if len(battery_payload) > 2 and battery_payload[2] in [0x31, 0x32, 0x33]:
        # Temporarily return a profile variant with BatteryAsciiCodec for legacy compatibility
        legacy_profile = DeviceProfile(
            name="OPPO Enco Buds3 Pro (Legacy ASCII)",
            battery_codec=BatteryAsciiCodec,
            firmware_codec=FirmwareBinaryCodec,
            supports_anc=False,
            supports_eq=True,
            supports_game_mode=True,
            supports_gestures=True,
            supports_find=True,
            supports_volume=True
        )
        return legacy_profile
    
    # 2. Check MAC address for the user's Enco Buds 3 Pro
    if mac_address and mac_address.upper() == "60:55:56:22:49:A0":
        return EncoBuds3ProProfile

    return DefaultLegacyProfile

