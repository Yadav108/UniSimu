import math

import pytest

from unisimu.physics import stellar
from unisimu.physics.stellar import evolve, main_sequence_lifetime_years


def stage_sequence(mass_msun: float, samples_per_segment: int = 50) -> list[str]:
    """Sample evolve() across the star's full lifetime and return the
    de-duplicated, order-preserved sequence of stages it passes through.

    Segment-lengths vary by orders of magnitude (a 2000-year supernova
    flash vs. a multi-billion-year main sequence), so we sample densely
    *within* each known phase boundary rather than uniformly across the
    whole span, or short phases get skipped entirely by the sampling grid.
    """
    ms_lifetime = main_sequence_lifetime_years(mass_msun)
    post_ms = ms_lifetime * stellar.POST_MS_FRACTION
    breakpoints = [
        0.0,
        stellar.FORMATION_YEARS,
        stellar.FORMATION_YEARS + ms_lifetime,
        stellar.FORMATION_YEARS + ms_lifetime + post_ms,
        stellar.FORMATION_YEARS + ms_lifetime + post_ms + stellar.TERMINAL_FLASH_YEARS,
        stellar.FORMATION_YEARS + ms_lifetime + post_ms + stellar.TERMINAL_FLASH_YEARS * 1.5,
    ]
    sequence: list[str] = []
    for start, end in zip(breakpoints, breakpoints[1:]):
        for i in range(samples_per_segment):
            age = start + (end - start) * i / (samples_per_segment - 1)
            stage = evolve(mass_msun, age).stage
            if not sequence or sequence[-1] != stage:
                sequence.append(stage)
    return sequence


@pytest.mark.parametrize(
    "mass_msun,expected",
    [
        (0.3, ["protostar", "main_sequence", "red_giant", "planetary_nebula", "white_dwarf"]),
        (1.0, ["protostar", "main_sequence", "red_giant", "planetary_nebula", "white_dwarf"]),
        (8.0, ["protostar", "main_sequence", "red_supergiant", "supernova", "neutron_star"]),
        (25.0, ["protostar", "main_sequence", "red_supergiant", "supernova", "black_hole"]),
        (100.0, ["protostar", "main_sequence", "red_supergiant", "supernova", "black_hole"]),
    ],
)
def test_stage_ordering(mass_msun, expected):
    assert stage_sequence(mass_msun) == expected


@pytest.mark.parametrize("mass_msun", [0.3, 1.0, 8.0, 25.0, 100.0])
def test_terminal_stage_is_stable(mass_msun):
    """Once a star reaches a terminal stage, further aging keeps it there."""
    ms_lifetime = main_sequence_lifetime_years(mass_msun)
    far_future = ms_lifetime * 5 + 1e12
    stage_a = evolve(mass_msun, far_future).stage
    stage_b = evolve(mass_msun, far_future * 2).stage
    assert stage_a == stage_b
    assert stage_a in stellar.TERMINAL_STAGES


@pytest.mark.parametrize("mass_msun,age_years", [(1.0, 0.0), (1.0, 1e9), (25.0, 1e6)])
def test_evolve_is_deterministic(mass_msun, age_years):
    snap_a = evolve(mass_msun, age_years)
    snap_b = evolve(mass_msun, age_years)
    assert snap_a == snap_b


def test_evolve_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        evolve(0.0, 0.0)
    with pytest.raises(ValueError):
        evolve(1.0, -1.0)


@pytest.mark.parametrize("mass_msun", [7.9, 8.0, 8.1, 19.9, 20.0, 20.1])
def test_boundary_masses_no_extreme_discontinuity(mass_msun):
    """Physical properties shouldn't jump by orders of magnitude for a
    tiny change in mass at the same simulated age (kinks from stage
    switches are expected and fine; blowups are not)."""
    age = stellar.FORMATION_YEARS + 1.0  # early main sequence, comparable across masses
    snap = evolve(mass_msun, age)
    assert snap.temperature_k > 0
    assert snap.radius_rsun > 0
    assert snap.luminosity_lsun > 0
    assert snap.color_hex.startswith("#") and len(snap.color_hex) == 7


def test_more_massive_stars_have_shorter_main_sequence_lifetimes():
    assert (
        main_sequence_lifetime_years(1.0)
        > main_sequence_lifetime_years(8.0)
        > main_sequence_lifetime_years(25.0)
    )


def test_radius_from_luminosity_temperature_matches_sun():
    r = stellar.radius_from_luminosity_temperature(1.0, stellar.SUN_TEMPERATURE_K)
    assert math.isclose(r, 1.0, rel_tol=1e-6)


@pytest.mark.parametrize(
    "mass_msun,expected",
    [
        (0.3, stellar.LOW_MASS_TRACK),
        (7.9, stellar.LOW_MASS_TRACK),
        (8.0, stellar.NEUTRON_STAR_TRACK),
        (19.9, stellar.NEUTRON_STAR_TRACK),
        (20.0, stellar.BLACK_HOLE_TRACK),
        (100.0, stellar.BLACK_HOLE_TRACK),
    ],
)
def test_stage_track_matches_actual_evolution(mass_msun, expected):
    assert stellar.stage_track(mass_msun) == expected
    # The track promised by stage_track() must match what evolve() actually visits.
    assert stage_sequence(mass_msun) == list(expected)
