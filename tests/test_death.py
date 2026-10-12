"""Tests for the death scenes (realism Phase 5): Type II-P light curve,
radioactive tail, planetary-nebula growth and emission-line colour."""

import math

import pytest

from unisimu.physics import death, stellar
from unisimu.physics.death import (
    DESSART_S15E12,
    emission_line_color,
    planetary_nebula_radius_pc,
    radioactive_luminosity_lsun,
    supernova_state,
)
from unisimu.physics.stellar import evolve

PROGENITOR = (6.8e4, 3519.0)  # Betelgeuse model at the end of its supergiant phase


def test_nothing_changes_before_shock_breakout():
    assert supernova_state(0.0, *PROGENITOR) == PROGENITOR
    assert supernova_state(0.99, *PROGENITOR) == PROGENITOR


def test_light_curve_passes_through_the_dessart_hillier_table():
    for day, temperature, lum_1e8 in DESSART_S15E12:
        lum, t = supernova_state(day, *PROGENITOR)
        assert lum == pytest.approx(lum_1e8 * 1e8, rel=1e-9)
        assert t == pytest.approx(temperature, rel=1e-9)


def test_plateau_lasts_about_a_hundred_days():
    # within ~0.3 dex of its level between day 20 and day 100
    early = supernova_state(20.0, *PROGENITOR)[0]
    late = supernova_state(100.0, *PROGENITOR)[0]
    assert abs(math.log10(early / late)) < 0.3
    # then it drops by about a dex within the following ~50 days
    assert supernova_state(150.0, *PROGENITOR)[0] < late / 4


def test_plateau_photosphere_sits_at_the_recombination_temperature():
    for day in range(50, 100, 10):
        assert 5000 < supernova_state(day, *PROGENITOR)[1] < 5600


def test_photospheric_radius_is_a_few_1e15_cm_on_the_plateau():
    lum, t = supernova_state(60.0, *PROGENITOR)
    radius_cm = stellar.radius_from_luminosity_temperature(lum, t) * 6.957e10
    assert 1e15 < radius_cm < 4e15  # Dessart & Hillier Table 4: 2.4-2.5e15 cm


def test_tail_follows_cobalt_decay():
    # e-folding over 111.3 d once nickel is gone (t >> 8.8 d)
    ratio = supernova_state(300.0, *PROGENITOR)[0] / supernova_state(200.0, *PROGENITOR)[0]
    assert ratio == pytest.approx(math.exp(-100.0 / death.COBALT_LIFETIME_DAYS), rel=0.02)


def test_decay_luminosity_matches_hand_calculation():
    # 1 M_sun of 56Ni at t = 0: eps_Ni = 3.90e10 erg/g/s -> 7.76e43 erg/s
    assert radioactive_luminosity_lsun(0.0, 1.0) * death.SOLAR_LUMINOSITY_ERG_S == pytest.approx(7.757e43, rel=1e-3)


def test_tail_joins_the_plateau_without_a_jump():
    last_day = DESSART_S15E12[-1][0]
    a = supernova_state(last_day, *PROGENITOR)[0]
    b = supernova_state(last_day + 0.5, *PROGENITOR)[0]
    assert abs(math.log10(a / b)) < 0.05


def test_evolve_supernova_stage_uses_the_light_curve_in_days():
    start = stellar.phase_schedule(16.5)[3][0]
    snap = evolve(16.5, start + 50.0 / death.DAYS_PER_YEAR)
    assert snap.stage == "supernova"
    progenitor_luminosity = stellar.main_sequence_luminosity(16.5) * stellar.RED_SUPERGIANT_BRIGHTENING
    expected = supernova_state(50.0, progenitor_luminosity, stellar.RED_SUPERGIANT_TEMPERATURE_K)
    assert snap.luminosity_lsun == pytest.approx(expected[0], rel=1e-6)
    assert snap.stage_progress == pytest.approx(50.0 / death.SUPERNOVA_LIGHT_CURVE_DAYS, rel=1e-6)


def test_terminal_phases_last_their_real_durations():
    sn = stellar.phase_schedule(16.5)[3]
    pn = stellar.phase_schedule(1.0)[3]
    assert (sn[1] - sn[0]) * death.DAYS_PER_YEAR == pytest.approx(400.0)
    assert pn[1] - pn[0] == pytest.approx(21_000.0)


def test_planetary_nebula_reaches_0_9_pc_in_its_visibility_time():
    # Jacob et al. 2013: 42 km/s, ~21 000 yr to R = 0.9 pc
    assert planetary_nebula_radius_pc(21_000.0) == pytest.approx(0.9, rel=0.01)


def test_planetary_nebula_colour_is_green_cyan():
    r, g, b = emission_line_color()
    assert g == max(r, g, b)  # [O III] 500.7 nm dominates
    assert b > r
    assert 0.2126 * r + 0.7152 * g + 0.0722 * b >= 1.0 - 1e-9


def test_pure_h_alpha_is_red():
    r, g, b = emission_line_color(((656.2804, 1.0),))
    assert r > 0 and g == 0 and b == 0


def test_neutron_star_radius_is_in_the_measured_range():
    # Ozel & Freire 2016: 9.9-11.2 km
    assert 9.9 <= stellar.NEUTRON_STAR_RADIUS_RSUN * stellar.SUN_RADIUS_KM <= 11.2
