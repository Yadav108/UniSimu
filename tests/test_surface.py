"""Tests for the stellar-surface physics (realism Phase 3). Reference values
come from docs/physics/equations/03-stellar-surface.md and the sources it cites."""

import math

import pytest

from unisimu.physics import limb_darkening_data as ld
from unisimu.physics.surface import (
    granulation_scale,
    granulation_visibility,
    granule_diameter_m,
    limb_darkening,
    pressure_scale_height_m,
    pulsation_period_days,
    spot_contrast,
    surface_gravity_cgs,
    temperature_sensitivity,
)


def test_solar_surface_gravity_is_log_g_4_44():
    assert surface_gravity_cgs(1.0, 1.0) == pytest.approx(4.438, abs=0.002)


def test_solar_pressure_scale_height_is_about_130_km():
    # mu = 1.3 neutral photosphere; the textbook value is ~100-150 km
    assert 100e3 < pressure_scale_height_m(5772, 1.0, 1.0) < 150e3


def test_betelgeuse_granules_are_vastly_larger_than_the_suns():
    sun = granule_diameter_m(5772, 1.0, 1.0)
    betelgeuse = granule_diameter_m(3519, 16.5, 705.0)
    assert betelgeuse / sun > 1e4  # "orders of magnitude"
    # and the giant has far fewer granules around its circumference
    assert granulation_scale(3519, 16.5, 705.0) < granulation_scale(5772, 1.0, 1.0) / 50


def test_hot_stars_have_no_granulation():
    assert granulation_visibility(5772) == 1.0
    assert granulation_visibility(30000) == 0.0
    assert 0.0 < granulation_visibility(9000) < 1.0


def test_limb_darkening_matches_the_claret_table_at_a_grid_point():
    # Claret & Bloemen (2011) tableab.dat, ATLAS, Z=0, xi=2, L: 5750 K, log g 4.5
    # B: a=0.6562 b=0.1546; V: a=0.4650 b=0.2565; R: a=0.3711 b=0.2775
    a_r, a_g, a_b, b_r, b_g, b_b = limb_darkening(5750, 4.5)
    assert (a_r, a_g, a_b) == pytest.approx((0.3711, 0.4650, 0.6562), abs=1e-4)
    assert (b_r, b_g, b_b) == pytest.approx((0.2775, 0.2565, 0.1546), abs=1e-4)


def _limb_intensity(coeffs, channel: int, mu: float) -> float:
    a, b = coeffs[channel], coeffs[channel + 3]
    return 1 - a * (1 - mu) - b * (1 - mu) ** 2


def test_blue_limb_darkens_more_than_red():
    for teff, logg in ((3500, 1.0), (5772, 4.44), (9000, 4.2), (30000, 4.0)):
        c = limb_darkening(teff, logg)
        assert _limb_intensity(c, 2, 0.3) < _limb_intensity(c, 0, 0.3)


def test_limb_darkening_effect_weakens_from_cool_to_hot_stars():
    # brightness at mu = 0.3 relative to the centre, V band, dwarfs
    darkening = [1 - _limb_intensity(limb_darkening(t, 4.5), 1, 0.3) for t in (4000, 6000, 10000, 20000, 40000)]
    assert all(a > b for a, b in zip(darkening, darkening[1:]))


def test_limb_profile_stays_physical_across_the_whole_grid():
    for row in ld.COEFFS:
        for coeffs in row:
            for ch in range(3):
                values = [_limb_intensity(coeffs, ch, mu / 20) for mu in range(21)]
                assert all(-1e-3 <= v <= 1.0 + 1e-9 for v in values)


def test_limb_darkening_clamps_outside_the_grid():
    assert limb_darkening(3050, 5.2) == pytest.approx(limb_darkening(3500, 5.0))
    assert limb_darkening(1e6, 8.0) == pytest.approx(limb_darkening(50000, 5.0))


def test_spot_contrast_is_the_planck_ratio():
    from unisimu.physics.blackbody import blackbody_linear_rgb
    from unisimu.physics.surface import SPOT_TEMPERATURE_RATIO

    t = 5772.0
    expected = [c / h for h, c in zip(blackbody_linear_rgb(t), blackbody_linear_rgb(t * SPOT_TEMPERATURE_RATIO))]
    assert spot_contrast(t) == pytest.approx(tuple(expected))
    r, g, b = spot_contrast(t)
    assert 0 < b < g < r < 1  # darker, and darkest in blue


def test_temperature_sensitivity_matches_wien_limit_for_cool_stars():
    # for h c / (lambda k T) >> 1, d ln B / d ln T ~ h c / (lambda k T): larger in blue
    r, g, b = temperature_sensitivity(3000)
    assert b > g > r > 3
    # and approaches 1 (Rayleigh-Jeans) for very hot surfaces
    assert all(0.8 < s < 1.6 for s in temperature_sensitivity(1e6))


def test_betelgeuse_fundamental_period_is_about_400_days():
    # Q = 0.085 d (Kiss, Szabo & Bedding 2006); observed ~400 d
    assert pulsation_period_days(16.5, 705.0) == pytest.approx(392, rel=0.01)
    assert pulsation_period_days(1.0, 1.0) == pytest.approx(0.085)


def test_period_scales_as_dynamical_time():
    assert pulsation_period_days(4.0, 400.0) / pulsation_period_days(1.0, 100.0) == pytest.approx(
        math.sqrt(400.0**3 / 4.0) / math.sqrt(100.0**3 / 1.0)
    )
