import pytest

from unisimu.presets import PRESETS, StarPreset


@pytest.mark.parametrize(
    "key,expected_fate",
    [
        ("proxima", "white_dwarf"),
        ("sun", "white_dwarf"),
        ("sirius", "white_dwarf"),
        ("betelgeuse", "neutron_star"),
        ("rigel", "black_hole"),
        ("eta_carinae", "black_hole"),
    ],
)
def test_preset_fate_matches_intended_bucket(key, expected_fate):
    preset = next(p for p in PRESETS if p.key == key)
    assert preset.fate_stage == expected_fate


def test_all_preset_keys_unique():
    keys = [p.key for p in PRESETS]
    assert len(keys) == len(set(keys))


def test_presets_cover_all_three_fates():
    fates = {p.fate_stage for p in PRESETS}
    assert fates == {"white_dwarf", "neutron_star", "black_hole"}


def test_preset_masses_positive():
    for preset in PRESETS:
        assert preset.mass_msun > 0


def test_star_preset_is_frozen():
    preset = PRESETS[0]
    with pytest.raises(AttributeError):
        preset.mass_msun = 999.0


def test_star_preset_directly_constructible():
    custom = StarPreset("test", "Test Star", 5.0, "blurb", "G2V")
    assert custom.fate_stage == "white_dwarf"
