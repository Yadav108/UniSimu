"""Tests for the honest time readouts (realism Phase 6)."""

import pytest

from unisimu.formatting import format_duration
from unisimu.physics import stellar
from unisimu.physics.stellar import cinematic_age_years, phase_schedule
from unisimu.physics.timekeeping import compression_range, stage_clock


@pytest.mark.parametrize(
    "years,expected",
    [
        (0, "0 d"),
        (0.5, "183 d"),
        (3.4, "3.4 yr"),
        (250, "250 yr"),
        (2000, "2 kyr"),
        (5e4, "50 kyr"),
        (1.04e9, "1.04 Gyr"),
        (6.84e11, "684 Gyr"),
        (3e14, "3.0×10⁵ Gyr"),
    ],
)
def test_format_duration(years, expected):
    assert format_duration(years) == expected


def test_format_duration_rejects_negative():
    with pytest.raises(ValueError):
        format_duration(-1)


@pytest.mark.parametrize("mass", [0.12, 1.0, 2.1, 16.5, 23.0, 90.0])
def test_stage_clock_matches_the_phase_schedule(mass):
    schedule = phase_schedule(mass)
    screen = 0.0
    for age_start, age_end, seconds in schedule:
        mid = cinematic_age_years(mass, screen + seconds / 2)
        clock = stage_clock(mass, mid)
        assert clock.stage_duration_years == pytest.approx(age_end - age_start)
        assert clock.stage_elapsed_years == pytest.approx((age_end - age_start) / 2, rel=1e-6)
        # the rate is exactly the phase's real duration over its screen time
        assert clock.years_per_screen_second == pytest.approx((age_end - age_start) / seconds)
        screen += seconds


def test_clock_stops_once_the_star_is_a_remnant():
    end = phase_schedule(1.0)[-1][1]
    clock = stage_clock(1.0, end + 1e6)
    assert clock.stage_duration_years is None
    assert clock.years_per_screen_second == 0.0
    assert clock.stage_elapsed_years == pytest.approx(1e6)


def test_suns_main_sequence_runs_at_half_a_billion_years_per_second():
    # 10 Gyr of main sequence in 20 screen seconds
    mid = cinematic_age_years(1.0, stellar.SCREEN_SECONDS_PROTOSTAR + 10)
    assert stage_clock(1.0, mid).years_per_screen_second == pytest.approx(
        stellar.main_sequence_lifetime_years(1.0) / stellar.SCREEN_SECONDS_MAIN_SEQUENCE
    )


def test_compression_spans_many_orders_of_magnitude_for_a_red_dwarf():
    slowest, fastest = compression_range(0.12)
    assert slowest == pytest.approx(stellar.terminal_flash_years(0.12) / stellar.SCREEN_SECONDS_TERMINAL_FLASH)
    assert fastest / slowest > 1e7
