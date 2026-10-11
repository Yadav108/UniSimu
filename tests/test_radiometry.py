"""Tests for the physically based blackbody colour path (realism Phase 1).

Oracle values come from docs/physics/equations/01-radiometry-color.md, which
derives them from the same published equations (Planck; Wyman, Sloan &
Shirley 2013 CIE fit; sRGB primaries from the ICC registry)."""

import math

import pytest

from unisimu.physics import stellar
from unisimu.physics.blackbody import (
    LINEAR_SRGB_TO_XYZ,
    REFERENCE_TEMPERATURE_K,
    XYZ_TO_LINEAR_SRGB,
    blackbody_display_color,
    blackbody_linear_rgb,
    chromaticity,
    cie1931_cmf,
    planck_spectral_radiance,
)


@pytest.mark.parametrize(
    "temperature_k,x,y",
    [
        (1667, 0.5613, 0.4065),
        (3000, 0.4358, 0.4052),
        (5772, 0.3263, 0.3361),
        (10000, 0.2807, 0.2884),
        (30000, 0.2502, 0.2488),
    ],
)
def test_chromaticity_matches_reference_table(temperature_k, x, y):
    cx, cy = chromaticity(temperature_k)
    assert cx == pytest.approx(x, abs=1e-3)
    assert cy == pytest.approx(y, abs=1e-3)


def test_planckian_locus_moves_monotonically_toward_blue():
    xs = [chromaticity(t)[0] for t in range(1667, 25001, 500)]
    assert all(a > b for a, b in zip(xs, xs[1:]))


def test_srgb_matrix_maps_d65_white_to_equal_rgb():
    d65 = (0.3127 / 0.3290, 1.0, (1 - 0.3127 - 0.3290) / 0.3290)
    rgb = [sum(XYZ_TO_LINEAR_SRGB[r][c] * d65[c] for c in range(3)) for r in range(3)]
    assert rgb == pytest.approx([1.0, 1.0, 1.0], abs=1e-9)


def test_srgb_luminance_row_matches_standard_weights():
    assert LINEAR_SRGB_TO_XYZ[1] == pytest.approx((0.2126, 0.7152, 0.0722), abs=1e-4)


def test_cmf_peaks_where_expected():
    # y-bar (photopic luminosity) peaks near 555 nm and is ~1 there
    peak = max(range(400, 701), key=lambda w: cie1931_cmf(w)[1])
    assert 550 <= peak <= 560
    assert cie1931_cmf(peak)[1] == pytest.approx(1.0, abs=0.02)


def test_sun_temperature_is_near_white():
    color, luminance = blackbody_display_color(5772)
    assert luminance == pytest.approx(1.0)
    assert min(color) / max(color) > 0.8


def test_3000k_is_orange_not_red():
    r, g, b = blackbody_display_color(3000)[0]
    assert r == max(r, g, b)
    assert 0.35 < g / r < 0.6
    assert b / r < 0.3


def test_30000k_is_blue_white():
    r, g, b = blackbody_display_color(30000)[0]
    assert b == max(r, g, b)
    assert r / b > 0.3


def test_luminance_strictly_increases_with_temperature():
    temps = [1500, 2000, 3000, 4000, 5772, 8000, 12000, 20000, 40000, 100000]
    lums = [blackbody_display_color(t)[1] for t in temps]
    assert all(a < b for a, b in zip(lums, lums[1:]))


def _luminance(rgb) -> float:
    return sum(LINEAR_SRGB_TO_XYZ[1][c] * v for c, v in enumerate(rgb))


def test_display_color_has_unit_luminance_and_no_negative_channels():
    for t in (3000, 9000, 60000):  # inside the sRGB gamut: nothing gets clipped
        color, _ = blackbody_display_color(t)
        assert min(color) >= 0
        assert _luminance(color) == pytest.approx(1.0, abs=1e-9)
    # 1200 K has a negative blue channel; clipping it can only add luminance
    color, _ = blackbody_display_color(1200)
    assert min(color) >= 0
    assert min(blackbody_linear_rgb(1200)) < 0
    assert _luminance(color) >= 1.0


def test_zero_temperature_emits_nothing():
    assert blackbody_display_color(0) == ((0.0, 0.0, 0.0), 0.0)
    assert blackbody_linear_rgb(0) == pytest.approx((0.0, 0.0, 0.0))


def test_extreme_temperatures_do_not_error():
    blackbody_display_color(1.0)
    blackbody_display_color(1e6)


def _bolometric(temperature_k: float) -> float:
    # integrate B_lambda over 10 nm .. 1 mm on a log grid; pi * integral = sigma T^4
    n = 4000
    lo, hi = math.log(10e-9), math.log(1e-3)
    total = 0.0
    for i in range(n):
        lam = math.exp(lo + (hi - lo) * (i + 0.5) / n)
        total += planck_spectral_radiance(lam, temperature_k) * lam * (hi - lo) / n
    return math.pi * total


def test_planck_integrates_to_stefan_boltzmann():
    sigma = 5.670_374_419e-8
    assert _bolometric(5772) == pytest.approx(sigma * 5772**4, rel=1e-3)


def test_bolometric_energy_scales_as_t_to_the_fourth():
    assert _bolometric(8000) / _bolometric(4000) == pytest.approx(16.0, rel=1e-3)


def test_snapshot_luminosity_radius_temperature_are_consistent():
    # L = 4 pi R^2 sigma T^4 in solar units, as used by evolve()
    for mass in (0.12, 1.0, 2.1, 16.5):
        snap = stellar.evolve(mass, stellar.FORMATION_YEARS * 2)
        expected = stellar.luminosity_from_radius_temperature(snap.radius_rsun, snap.temperature_k)
        assert snap.luminosity_lsun == pytest.approx(expected, rel=1e-6)


def test_reference_temperature_is_iau_nominal():
    assert REFERENCE_TEMPERATURE_K == 5772.0
