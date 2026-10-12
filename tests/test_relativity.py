"""Tests for the Schwarzschild optics (realism Phase 4). The renderer's GLSL
integrator mirrors relativity.trace_ray, so these also pin the shader's maths."""

import math

import pytest

from unisimu.physics.relativity import (
    COLOR_TABLE_SIZE,
    CRITICAL_IMPACT_PARAMETER_M,
    HORIZON_RADIUS_M,
    ISCO_RADIUS_M,
    PHOTON_SPHERE_RADIUS_M,
    blackbody_color_table,
    bolometric_intensity_ratio,
    circular_orbit_redshift,
    deflection_angle,
    disk_temperature,
    impact_parameter,
    shadow_angular_radius,
    trace_ray,
)


def test_characteristic_radii():
    assert HORIZON_RADIUS_M == 2.0
    assert PHOTON_SPHERE_RADIUS_M == 3.0
    assert ISCO_RADIUS_M == 6.0
    assert CRITICAL_IMPACT_PARAMETER_M == pytest.approx(5.196152, abs=1e-6)


def _traced_shadow_edge(r_observer: float) -> float:
    """Bisect the angle (from the inward direction) where rays stop falling in."""
    lo, hi = 0.0, math.pi / 2
    for _ in range(30):
        mid = (lo + hi) / 2
        if trace_ray(r_observer, math.pi - mid, step=0.002).fate == "horizon":
            lo = mid
        else:
            hi = mid
    return lo


@pytest.mark.parametrize("r_observer", [10.0, 30.0, 100.0])
def test_traced_shadow_matches_synges_formula(r_observer):
    assert _traced_shadow_edge(r_observer) == pytest.approx(shadow_angular_radius(r_observer), abs=2e-5)


def test_far_shadow_radius_is_the_critical_impact_parameter():
    r = 1e6
    assert shadow_angular_radius(r) * r == pytest.approx(CRITICAL_IMPACT_PARAMETER_M, rel=1e-5)
    # and the edge ray's impact parameter is b_c at any distance
    for r_observer in (10.0, 50.0):
        alpha = math.pi - shadow_angular_radius(r_observer)
        assert impact_parameter(r_observer, alpha) == pytest.approx(CRITICAL_IMPACT_PARAMETER_M, rel=1e-9)


def test_weak_field_bending_is_4m_over_b():
    assert deflection_angle(1000.0, step=2e-3) == pytest.approx(4.0 / 1000.0, rel=0.01)


def test_bending_grows_toward_the_photon_sphere():
    angles = [deflection_angle(b, step=2e-3) for b in (100.0, 30.0, 10.0, 6.0)]
    assert all(a < b for a, b in zip(angles, angles[1:]))
    assert deflection_angle(5.3, step=5e-4) > math.pi / 2  # near b_c light swings around the hole


def test_rays_inside_the_shadow_fall_in():
    assert trace_ray(30.0, math.pi).fate == "horizon"  # straight at the hole
    assert trace_ray(30.0, math.pi - 0.9 * shadow_angular_radius(30.0)).fate == "horizon"
    assert trace_ray(30.0, math.pi - 1.1 * shadow_angular_radius(30.0)).fate == "escape"


def test_disc_plane_crossings_are_reported():
    # a ray grazing past the hole crosses a disc plane edge-on to the observer
    result = trace_ray(30.0, math.pi - 0.3, plane_phi0=math.pi / 2)
    assert result.fate == "escape"
    assert result.crossings and all(r > HORIZON_RADIUS_M for _, r in result.crossings)


def test_redshift_vanishes_far_away_with_no_motion():
    assert circular_orbit_redshift(1e9, 0.0) == pytest.approx(1.0, abs=1e-8)


def test_face_on_isco_light_is_redshifted_by_root_two():
    # lam = 0: only gravitational + transverse Doppler: sqrt(1 - 3M/6M)
    assert circular_orbit_redshift(ISCO_RADIUS_M, 0.0) == pytest.approx(math.sqrt(0.5))


def test_approaching_side_is_brighter_by_g_to_the_fourth():
    lam = 0.8 * CRITICAL_IMPACT_PARAMETER_M
    g_toward = circular_orbit_redshift(8.0, +lam)
    g_away = circular_orbit_redshift(8.0, -lam)
    # this close in, gravity redshifts even the approaching side (g < 1),
    # but it is still far brighter than the receding side
    assert g_away < g_toward < 1.0
    ratio = bolometric_intensity_ratio(g_toward) / bolometric_intensity_ratio(g_away)
    assert ratio == pytest.approx((g_toward / g_away) ** 4)
    assert ratio > 4


def test_static_observer_sees_extra_blueshift():
    assert circular_orbit_redshift(8.0, 0.0, r_observer=30.0) == pytest.approx(
        circular_orbit_redshift(8.0, 0.0) / math.sqrt(1 - 2 / 30.0)
    )


def test_disk_temperature_profile():
    r_in = ISCO_RADIUS_M
    assert disk_temperature(r_in, r_in, 1e7) == 0.0
    assert disk_temperature(49 / 36 * r_in, r_in, 1e7) == pytest.approx(1e7)
    outer = [disk_temperature(r, r_in, 1e7) for r in (10, 15, 20, 40)]
    assert all(a > b for a, b in zip(outer, outer[1:]))
    # far out, T ~ r^(-3/4)
    assert disk_temperature(1e4, r_in, 1.0) / disk_temperature(2e4, r_in, 1.0) == pytest.approx(2**0.75, rel=1e-2)


def test_color_table_spans_cool_to_very_hot_and_brightens():
    table = blackbody_color_table()
    assert len(table) == COLOR_TABLE_SIZE * 4
    log_lum = table[3::4]
    assert all(a < b for a, b in zip(log_lum, log_lum[1:]))
    r_cool, _, b_cool = table[0], table[1], table[2]
    r_hot, b_hot = table[-4], table[-2]
    assert r_cool > b_cool and b_hot > r_hot
