from oppo_control.cli import (
    EQ_CHOICES,
    GESTURE_ACTION_CHOICES,
    GESTURE_EAR_CHOICES,
    GESTURE_FUNCTION_CHOICES,
    GESTURE_TRIGGER_CHOICES,
)
from oppo_control.commands import EQPreset


def test_every_cli_eq_choice_maps_to_an_enum_member():
    """Every argparse choice must resolve; 'treble' is not an enum member name."""
    for name in ("original", "bass", "treble", "vocal", "bass_boost", "treble_boost"):
        assert isinstance(EQ_CHOICES[name], EQPreset)


def test_gesture_cli_choices_map_to_wire_ids():
    """The CLI names must resolve to the same IDs the matrix uses."""
    assert GESTURE_EAR_CHOICES == {"left": 1, "right": 2}
    assert GESTURE_ACTION_CHOICES == {"basic": 1, "custom": 6}
    assert GESTURE_TRIGGER_CHOICES == {
        "single": 1, "double": 2, "triple": 3,
        "long": 4, "double_hold": 5, "slide": 6,
    }
    assert GESTURE_FUNCTION_CHOICES["none"] == 0x00
    assert GESTURE_FUNCTION_CHOICES["play_pause"] == 0x01
    assert GESTURE_FUNCTION_CHOICES["voice_assistant"] == 0x03
    assert GESTURE_FUNCTION_CHOICES["game_mode"] == 0x11
    assert GESTURE_FUNCTION_CHOICES["game_mode_toggle_alt"] == 0x1D
