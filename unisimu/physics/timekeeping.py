"""Honest time readouts for the cinematic clock (realism Phase 6).

The simulation squeezes a star's life -- from a ~2000-year supernova to a
trillion-year red dwarf -- into about 50 screen seconds, using the fixed
per-phase screen times in stellar.phase_schedule(). That compression is kept;
this module only reports it truthfully: how much real time the current stage
has taken, how long it lasts, and how many real years one screen second
currently stands for. See docs/physics/equations/06-time.md.
"""

from dataclasses import dataclass

from unisimu.physics.stellar import phase_schedule


@dataclass(frozen=True)
class StageClock:
    stage_elapsed_years: float  # real time since the current timed phase began
    stage_duration_years: float | None  # None once the star is a remnant (open-ended)
    years_per_screen_second: float  # at 1x playback; 0 once the clock has stopped


def stage_clock(mass_msun: float, age_years: float) -> StageClock:
    """Where `age_years` falls in the phase schedule, in real units."""
    schedule = phase_schedule(mass_msun)
    for age_start, age_end, screen_seconds in schedule:
        if age_years < age_end:
            elapsed = max(age_years - age_start, 0.0)
            return StageClock(elapsed, age_end - age_start, (age_end - age_start) / screen_seconds)
    remnant_start = schedule[-1][1]
    return StageClock(max(age_years - remnant_start, 0.0), None, 0.0)


def compression_range(mass_msun: float) -> tuple[float, float]:
    """Slowest and fastest clock rates (years per screen second) over the
    star's life: how unevenly the cinematic clock treats its phases."""
    rates = [(end - start) / seconds for start, end, seconds in phase_schedule(mass_msun)]
    return min(rates), max(rates)
