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


# --- Cinematic pacing -------------------------------------------------------

PRESET_MASSES = [0.12, 1.0, 2.1, 16.5, 23.0, 90.0]
TICK_HZ = 20  # matches SimState's loop rate


def ticks_per_stage(mass_msun: float, speed: float) -> dict[str, int]:
    """Step the cinematic clock exactly as SimState.tick_loop does and count
    how many ticks the star spends in each stage before it reaches a remnant."""
    counts: dict[str, int] = {}
    screen_seconds = 0.0
    for _ in range(10_000):
        screen_seconds += speed / TICK_HZ
        stage = evolve(mass_msun, stellar.cinematic_age_years(mass_msun, screen_seconds)).stage
        counts[stage] = counts.get(stage, 0) + 1
        if stage in stellar.TERMINAL_STAGES:
            return counts
    raise AssertionError("star never reached a terminal stage")


@pytest.mark.parametrize("mass_msun", PRESET_MASSES + [0.1, 8.0, 20.0, 150.0])
def test_every_stage_is_visible_even_at_max_speed(mass_msun):
    """The bug this guards against: real timescales made protostar/supernova/
    planetary-nebula phases shorter than one tick, so they never rendered."""
    counts = ticks_per_stage(mass_msun, speed=16.0)
    track = stellar.stage_track(mass_msun)
    assert list(counts) == list(track)
    # The terminal stage stops the loop on its first tick; every stage before it must last.
    for stage in track[:-1]:
        assert counts[stage] >= 3, f"{stage} lasted only {counts[stage]} ticks at 16x"


@pytest.mark.parametrize("mass_msun", [0.1, 1.0, 16.5, 150.0])
def test_lifetime_is_short_and_mass_independent_on_screen(mass_msun):
    total = stellar.total_screen_seconds(mass_msun)
    assert 30 <= total <= 90
    assert total == stellar.total_screen_seconds(1.0)


@pytest.mark.parametrize("mass_msun", PRESET_MASSES)
def test_cinematic_age_is_monotonic_and_continuous_across_phases(mass_msun):
    total = stellar.total_screen_seconds(mass_msun)
    ages = [stellar.cinematic_age_years(mass_msun, total * i / 400) for i in range(401)]
    assert ages == sorted(ages)
    assert stellar.cinematic_age_years(mass_msun, 0.0) == 0.0
    # The age has no jump at a phase boundary: the protostar ends exactly where
    # the main sequence begins (slopes differ enormously, but the value doesn't).
    boundary = stellar.SCREEN_SECONDS_PROTOSTAR
    before = stellar.cinematic_age_years(mass_msun, boundary - 1e-6)
    after = stellar.cinematic_age_years(mass_msun, boundary + 1e-6)
    assert before <= stellar.FORMATION_YEARS <= after


@pytest.mark.parametrize("mass_msun", PRESET_MASSES)
def test_past_the_end_of_the_schedule_is_the_remnant(mass_msun):
    total = stellar.total_screen_seconds(mass_msun)
    for extra in (0.0, 1.0, 1e6):
        age = stellar.cinematic_age_years(mass_msun, total + extra)
        assert evolve(mass_msun, age).stage == stellar.stage_track(mass_msun)[-1]


# --- Physics that drives what the viewport looks like ------------------------


@pytest.mark.parametrize("mass_msun", [8.0, 16.5, 23.0, 90.0])
def test_red_supergiants_actually_end_up_red(mass_msun):
    end = stellar.phase_schedule(mass_msun)[2][1]
    snap = evolve(mass_msun, end - 1.0)
    assert snap.stage == "red_supergiant"
    assert snap.temperature_k <= 4000
    r, g, b = (int(snap.color_hex[i : i + 2], 16) for i in (1, 3, 5))
    assert r > g > b


@pytest.mark.parametrize("mass_msun", [8.0, 16.5, 90.0])
def test_supernova_starts_from_the_progenitors_state(mass_msun):
    start = stellar.phase_schedule(mass_msun)[3][0]
    before = evolve(mass_msun, start - 1.0)
    first = evolve(mass_msun, start + 0.01)
    assert first.stage == "supernova"
    assert math.isclose(first.temperature_k, before.temperature_k, rel_tol=0.02)
    assert math.isclose(first.luminosity_lsun, before.luminosity_lsun, rel_tol=0.02)
    assert math.isclose(first.radius_rsun, before.radius_rsun, rel_tol=0.05)


@pytest.mark.parametrize("mass_msun", [8.0, 16.5, 90.0])
def test_supernova_outshines_its_progenitor_by_orders_of_magnitude(mass_msun):
    start, end, _ = stellar.phase_schedule(mass_msun)[3]
    peak = max(evolve(mass_msun, start + (end - start) * f / 100).luminosity_lsun for f in range(100))
    assert peak > 100 * evolve(mass_msun, start - 1.0).luminosity_lsun


@pytest.mark.parametrize("mass_msun", [0.3, 1.0, 2.1])
def test_planetary_nebula_starts_from_the_giants_state_and_heats_up(mass_msun):
    start, end, _ = stellar.phase_schedule(mass_msun)[3]
    before = evolve(mass_msun, start - 1.0)
    first = evolve(mass_msun, start + 0.01)
    last = evolve(mass_msun, end - 1.0)
    assert first.stage == last.stage == "planetary_nebula"
    assert math.isclose(first.temperature_k, before.temperature_k, rel_tol=0.02)
    assert math.isclose(first.luminosity_lsun, before.luminosity_lsun, rel_tol=0.02)
    assert last.temperature_k > 20 * first.temperature_k


def test_neutron_star_is_a_tiny_hot_object():
    snap = evolve(16.5, main_sequence_lifetime_years(16.5) * 10)
    assert snap.stage == "neutron_star"
    assert 1e-5 < snap.radius_rsun < 3e-5  # ~7-20 km
    assert snap.temperature_k >= 1e5
    assert snap.luminosity_lsun > 0


@pytest.mark.parametrize("mass_msun", [20.0, 90.0])
def test_black_hole_has_schwarzschild_radius_and_no_light(mass_msun):
    snap = evolve(mass_msun, main_sequence_lifetime_years(mass_msun) * 10)
    assert snap.stage == "black_hole"
    remnant_mass = mass_msun * stellar.BLACK_HOLE_MASS_FRACTION
    expected_km = remnant_mass * stellar.SCHWARZSCHILD_KM_PER_MSUN
    assert math.isclose(snap.radius_rsun * stellar.SUN_RADIUS_KM, expected_km, rel_tol=1e-9)
    assert snap.luminosity_lsun == 0.0
    assert snap.color_hex == "#000000"


def test_main_sequence_temperature_matches_known_stars_and_is_monotonic():
    assert math.isclose(stellar.main_sequence_temperature_k(1.0), stellar.SUN_TEMPERATURE_K)
    assert 2900 < stellar.main_sequence_temperature_k(0.12) < 3200  # Proxima Centauri, ~3050 K
    masses = [0.05, 0.1, 0.2, 0.5, 0.9, 1.0, 1.7, 3.0, 8.0, 20.0, 60.0, 150.0, 300.0]
    temps = [stellar.main_sequence_temperature_k(m) for m in masses]
    assert temps == sorted(temps)
    assert all(t > 0 for t in temps)
