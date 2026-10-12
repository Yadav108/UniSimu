"""Tests for realism Phase 7: red dwarfs become blue dwarfs (issue #11) and
white dwarfs cool by the Mestel law (issue #12)."""

import pytest

from unisimu.copy import STAGE_CAPTIONS, STAGE_LABELS
from unisimu.physics import remnants, stellar
from unisimu.physics.stellar import evolve, phase_schedule, stage_track


def _sample(mass: float, per_phase: int = 60):
    """Snapshots spread through every timed phase plus 13 Gyr of remnant life."""
    snaps = []
    for start, end, _ in phase_schedule(mass):
        snaps += [evolve(mass, start + (end - start) * i / per_phase) for i in range(per_phase)]
    remnant = phase_schedule(mass)[-1][1]
    snaps += [evolve(mass, remnant + t) for t in (1.0, 1e6, 1e9, 1.3e10)]
    return snaps


# --- issue #11: no red giant below 0.25 M_sun ---------------------------------

@pytest.mark.parametrize("mass", [0.1, 0.12, 0.2, 0.24])
def test_red_dwarfs_never_become_red_giants(mass):
    assert stage_track(mass) == stellar.RED_DWARF_TRACK
    stages = [s.stage for s in _sample(mass)]
    assert "red_giant" not in stages and "planetary_nebula" not in stages
    order = [s for i, s in enumerate(stages) if i == 0 or stages[i - 1] != s]
    assert order == list(stellar.RED_DWARF_TRACK)


def test_the_threshold_is_a_quarter_of_a_solar_mass():
    assert stage_track(0.249) == stellar.RED_DWARF_TRACK
    assert stage_track(0.25) == stellar.LOW_MASS_TRACK


def test_proxima_stays_small_instead_of_swelling_to_four_solar_radii():
    snaps = _sample(0.12)
    ms_radius = evolve(0.12, phase_schedule(0.12)[1][0] + 1.0).radius_rsun
    assert max(s.radius_rsun for s in snaps if s.stage != "protostar") <= ms_radius * 1.0001


def test_blue_dwarf_heats_to_the_lba_peak_and_stays_faint():
    blue = [s for s in _sample(0.12, per_phase=400) if s.stage == "blue_dwarf"]
    assert max(s.temperature_k for s in blue) == pytest.approx(stellar.BLUE_DWARF_PEAK_TEMPERATURE_K, rel=1e-3)
    assert max(s.luminosity_lsun for s in blue) <= stellar.BLUE_DWARF_PEAK_LUMINOSITY_LSUN * 1.0001


def test_blue_dwarf_has_a_caption_and_label():
    for stage in stellar.RED_DWARF_TRACK:
        assert stage in STAGE_LABELS
    for stage in stellar.RED_DWARF_TRACK[1:]:
        assert STAGE_CAPTIONS.get(stage)


# --- issue #12: white dwarfs cool -------------------------------------------

def test_mestel_reproduces_kawalers_worked_example_within_30_percent():
    # 0.6 M_sun, A = 14, mu = 1.4, L = 10^-4.5 L_sun: Kawaler quotes ~7 Gyr and
    # says Mestel is within ~30 % of detailed models
    assert remnants.cooling_time_years(10**-4.5) == pytest.approx(7e9, rel=0.3)


def test_cooling_time_scales_as_l_to_the_minus_five_sevenths():
    ratio = remnants.cooling_time_years(1e-3) / remnants.cooling_time_years(1e-2)
    assert ratio == pytest.approx(10 ** (5 / 7))


def test_cooling_starts_at_the_birth_luminosity_and_only_fades():
    assert remnants.cooled_luminosity_lsun(0.0, 10.0) == pytest.approx(10.0)
    lums = [remnants.cooled_luminosity_lsun(t, 10.0) for t in (0, 1e5, 1e7, 1e9, 1e10)]
    assert all(a > b for a, b in zip(lums, lums[1:]))


@pytest.mark.parametrize("mass", [0.12, 1.0, 2.1])
def test_white_dwarf_cools_and_reddens_with_age(mass):
    remnant = phase_schedule(mass)[-1][1]
    young = evolve(mass, remnant + 1.0)
    old = evolve(mass, remnant + 1.0e10)
    assert young.stage == old.stage == "white_dwarf"
    assert old.temperature_k < 0.75 * young.temperature_k
    assert old.luminosity_lsun < young.luminosity_lsun / 5
    assert old.radius_rsun == young.radius_rsun == stellar.WHITE_DWARF_RADIUS_RSUN


@pytest.mark.parametrize("mass", [0.12, 1.0])
def test_white_dwarf_birth_continues_the_previous_stage(mass):
    remnant = phase_schedule(mass)[-1][1]
    last = evolve(mass, remnant - 1e-6 * (remnant - phase_schedule(mass)[-1][0]))
    first = evolve(mass, remnant + 1.0)
    assert last.stage != "white_dwarf" and first.stage == "white_dwarf"
    assert first.luminosity_lsun == pytest.approx(last.luminosity_lsun, rel=0.02)
    # luminosity hands over exactly; the temperature may step by a few percent
    # where the previous stage's radius differs from the white-dwarf radius
    assert first.temperature_k == pytest.approx(last.temperature_k, rel=0.1)


def test_ten_billion_year_old_white_dwarf_is_a_few_thousand_kelvin():
    snap = evolve(1.0, phase_schedule(1.0)[-1][1] + 1.0e10)
    assert 3000 < snap.temperature_k < 5000
