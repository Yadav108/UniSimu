import pytest

from unisimu.physics.blackbody import kelvin_to_hex, kelvin_to_rgb


def test_hot_temperature_is_blue_dominant():
    r, g, b = kelvin_to_rgb(20000)
    assert b >= r


def test_cool_temperature_is_red_dominant():
    r, g, b = kelvin_to_rgb(1500)
    assert r > b


def test_sun_like_temperature_is_roughly_white():
    r, g, b = kelvin_to_rgb(5778)
    assert max(r, g, b) - min(r, g, b) < 40


@pytest.mark.parametrize("temperature_k", [1000, 3000, 5778, 10000, 20000, 40000])
def test_rgb_components_in_valid_range(temperature_k):
    for channel in kelvin_to_rgb(temperature_k):
        assert 0 <= channel <= 255


def test_hex_format():
    hex_color = kelvin_to_hex(5778)
    assert hex_color.startswith("#")
    assert len(hex_color) == 7
    int(hex_color[1:], 16)  # raises if not valid hex


def test_deterministic():
    assert kelvin_to_hex(6000) == kelvin_to_hex(6000)


def test_extreme_inputs_are_clamped_not_erroring():
    kelvin_to_rgb(0)
    kelvin_to_rgb(1_000_000)
