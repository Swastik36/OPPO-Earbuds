from oppo_control.cli import EQ_CHOICES
from oppo_control.commands import EQPreset


def test_every_cli_eq_choice_maps_to_an_enum_member():
    """Every argparse choice must resolve; 'treble' is not an enum member name."""
    for name in ("original", "bass", "treble", "vocal", "bass_boost", "treble_boost"):
        assert isinstance(EQ_CHOICES[name], EQPreset)
