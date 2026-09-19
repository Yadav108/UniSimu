"""Simplified single-star stellar evolution model.

Deterministic, dependency-free: evolve(mass_msun, age_years) is a pure
function of (initial mass, elapsed simulated time) using standard
simplified astrophysics scaling relations rather than a full stellar
structure integration. Good enough to drive a plausible, mass-dependent
visualization; not a research-grade model.

Stage thresholds by initial mass:
  < 8 M_sun   -> red giant -> planetary nebula -> white dwarf
  8-20 M_sun  -> red supergiant -> supernova -> neutron star
  >= 20 M_sun -> red supergiant -> supernova -> black hole

Real stellar lifetimes span twelve orders of magnitude and the dramatic
phases (a supernova lasts weeks; a planetary nebula, ~10^4 years) are tiny
slivers of a main-sequence life, so a linear simulated clock would blow
straight past them. `cinematic_age_years` maps a screen-time clock onto
simulated age with a fixed on-screen duration per phase instead.
"""

import math
from dataclasses import dataclass

from unisimu.physics.blackbody import kelvin_to_hex

SUN_TEMPERATURE_K = 5778.0
SUN_RADIUS_KM = 695_700.0
SCHWARZSCHILD_KM_PER_MSUN = 2.953

FORMATION_YEARS = 5.0e4
POST_MS_FRACTION = 0.10
TERMINAL_FLASH_YEARS = 2.0e3

SUPERGIANT_MASS_THRESHOLD = 8.0
BLACK_HOLE_MASS_THRESHOLD = 20.0

# Post-main-sequence: giants swell and cool to ~3000 K (deep red) but a low-
# mass giant brightens enormously (L ~ x1000) while a supergiant runs
# roughly horizontally across the H-R diagram (L ~ x2.5).
RED_GIANT_TIP_TEMPERATURE_K = 3200.0
RED_GIANT_MAX_BRIGHTENING = 1000.0
RED_GIANT_TIP_LUMINOSITY_CAP_LSUN = 2500.0
RED_SUPERGIANT_TEMPERATURE_K = 3500.0
RED_SUPERGIANT_BRIGHTENING = 2.5

# Planetary nebula: the ejected envelope exposes a core that heats at roughly
# constant luminosity before nuclear burning shuts off.
PLANETARY_NEBULA_CORE_TEMPERATURE_K = 1.0e5
PLANETARY_NEBULA_FADE_FRACTION = 0.01
WHITE_DWARF_TEMPERATURE_K = 25000.0
WHITE_DWARF_RADIUS_RSUN = 0.012

# Supernova light curve: fast shock-breakout rise, then a decay while the
# photosphere cools from ~60,000 K to ~6,000 K.
SUPERNOVA_PEAK_LUMINOSITY_LSUN = 3.0e9
SUPERNOVA_RISE_FRACTION = 0.07
SUPERNOVA_PEAK_TEMPERATURE_K = 6.0e4
SUPERNOVA_LATE_TEMPERATURE_K = 6000.0
SUPERNOVA_DECAY_RATE = 5.0

NEUTRON_STAR_RADIUS_RSUN = 1.7e-5  # ~12 km
NEUTRON_STAR_TEMPERATURE_K = 1.0e6
BLACK_HOLE_MASS_FRACTION = 0.35  # remnant mass as a fraction of the progenitor's

# Cinematic pacing: seconds of screen time each phase occupies at 1x speed,
# independent of the star's real timescales.
SCREEN_SECONDS_PROTOSTAR = 6.0
SCREEN_SECONDS_MAIN_SEQUENCE = 20.0
SCREEN_SECONDS_POST_MAIN_SEQUENCE = 14.0
SCREEN_SECONDS_TERMINAL_FLASH = 10.0

STAGES = (
    "protostar",
    "main_sequence",
    "red_giant",
    "red_supergiant",
    "supernova",
    "planetary_nebula",
    "white_dwarf",
    "neutron_star",
    "black_hole",
)

TERMINAL_STAGES = frozenset({"white_dwarf", "neutron_star", "black_hole"})

LOW_MASS_TRACK = ("protostar", "main_sequence", "red_giant", "planetary_nebula", "white_dwarf")
NEUTRON_STAR_TRACK = ("protostar", "main_sequence", "red_supergiant", "supernova", "neutron_star")
BLACK_HOLE_TRACK = ("protostar", "main_sequence", "red_supergiant", "supernova", "black_hole")

# (initial mass in M_sun, main-sequence effective temperature in K), roughly
# the observed spectral-type sequence M -> O. Interpolated log-log below.
_MS_TEMPERATURE_ANCHORS = (
    (0.1, 2900.0),
    (0.12, 3050.0),
    (0.3, 3400.0),
    (0.5, 3800.0),
    (0.8, 5000.0),
    (1.0, SUN_TEMPERATURE_K),
    (1.5, 6900.0),
    (2.0, 8900.0),
    (3.0, 12000.0),
    (5.0, 16000.0),
    (10.0, 25000.0),
    (20.0, 33000.0),
    (40.0, 41000.0),
    (90.0, 47000.0),
    (150.0, 50000.0),
)


def stage_track(mass_msun: float) -> tuple[str, ...]:
    """The ordered sequence of life stages this mass will pass through,
    for driving a timeline/progress UI."""
    if mass_msun < SUPERGIANT_MASS_THRESHOLD:
        return LOW_MASS_TRACK
    if mass_msun < BLACK_HOLE_MASS_THRESHOLD:
        return NEUTRON_STAR_TRACK
    return BLACK_HOLE_TRACK


@dataclass(frozen=True)
class StellarSnapshot:
    stage: str
    radius_rsun: float
    temperature_k: float
    luminosity_lsun: float
    color_hex: str
    stage_progress: float  # 0..1 within the current stage


def main_sequence_luminosity(mass_msun: float) -> float:
    """Piecewise mass-luminosity relation, L in solar units."""
    m = mass_msun
    if m < 0.43:
        return 0.23 * m**2.3
    if m < 2.0:
        return m**4.0
    if m < 20.0:
        return 1.5 * m**3.5
    return 3200.0 * m


def main_sequence_lifetime_years(mass_msun: float) -> float:
    return 1.0e10 * mass_msun / main_sequence_luminosity(mass_msun)


def main_sequence_temperature_k(mass_msun: float) -> float:
    first_mass, first_temp = _MS_TEMPERATURE_ANCHORS[0]
    if mass_msun <= first_mass:
        return first_temp * (mass_msun / first_mass) ** 0.3
    for (m0, t0), (m1, t1) in zip(_MS_TEMPERATURE_ANCHORS, _MS_TEMPERATURE_ANCHORS[1:]):
        if mass_msun <= m1:
            return _geometric(t0, t1, math.log(mass_msun / m0) / math.log(m1 / m0))
    return _MS_TEMPERATURE_ANCHORS[-1][1]


def radius_from_luminosity_temperature(luminosity_lsun: float, temperature_k: float) -> float:
    """Stefan-Boltzmann: L = 4*pi*R^2*sigma*T^4 => R/Rsun = sqrt(L/Lsun) * (Tsun/T)^2."""
    l = max(luminosity_lsun, 1e-6)
    return math.sqrt(l) * (SUN_TEMPERATURE_K / temperature_k) ** 2


def luminosity_from_radius_temperature(radius_rsun: float, temperature_k: float) -> float:
    """Inverse of radius_from_luminosity_temperature."""
    return radius_rsun**2 * (temperature_k / SUN_TEMPERATURE_K) ** 4


def _geometric(start: float, end: float, frac: float) -> float:
    """Interpolate between two positive values in log space -- the natural
    way for temperature and luminosity to move on an H-R diagram."""
    return start * (end / start) ** frac


def _smoothstep(x: float, lo: float, hi: float) -> float:
    t = max(0.0, min(1.0, (x - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def _red_giant_tip_luminosity(ms_luminosity: float) -> float:
    brightening = min(RED_GIANT_MAX_BRIGHTENING, max(1.0, RED_GIANT_TIP_LUMINOSITY_CAP_LSUN / ms_luminosity))
    return ms_luminosity * brightening


def _supernova_light_curve(frac: float, pre_luminosity: float) -> tuple[float, float]:
    """(luminosity, temperature) `frac` (0..1) of the way through the
    supernova, starting continuously from the progenitor's own state."""
    if frac < SUPERNOVA_RISE_FRACTION:
        x = frac / SUPERNOVA_RISE_FRACTION
        return (
            _geometric(pre_luminosity, SUPERNOVA_PEAK_LUMINOSITY_LSUN, x),
            _geometric(RED_SUPERGIANT_TEMPERATURE_K, SUPERNOVA_PEAK_TEMPERATURE_K, x),
        )
    x = (frac - SUPERNOVA_RISE_FRACTION) / (1 - SUPERNOVA_RISE_FRACTION)
    return (
        SUPERNOVA_PEAK_LUMINOSITY_LSUN * math.exp(-SUPERNOVA_DECAY_RATE * x),
        _geometric(SUPERNOVA_PEAK_TEMPERATURE_K, SUPERNOVA_LATE_TEMPERATURE_K, x),
    )


def _black_hole_snapshot(mass_msun: float) -> StellarSnapshot:
    remnant_mass = mass_msun * BLACK_HOLE_MASS_FRACTION
    radius = remnant_mass * SCHWARZSCHILD_KM_PER_MSUN / SUN_RADIUS_KM
    hawking_temperature = 6.2e-8 / remnant_mass
    return StellarSnapshot("black_hole", radius, hawking_temperature, 0.0, "#000000", 1.0)


def _neutron_star_snapshot() -> StellarSnapshot:
    luminosity = luminosity_from_radius_temperature(NEUTRON_STAR_RADIUS_RSUN, NEUTRON_STAR_TEMPERATURE_K)
    return StellarSnapshot(
        "neutron_star", NEUTRON_STAR_RADIUS_RSUN, NEUTRON_STAR_TEMPERATURE_K, luminosity,
        kelvin_to_hex(NEUTRON_STAR_TEMPERATURE_K), 1.0,
    )


def evolve(mass_msun: float, age_years: float) -> StellarSnapshot:
    if mass_msun <= 0:
        raise ValueError("mass_msun must be positive")
    if age_years < 0:
        raise ValueError("age_years must be non-negative")

    m = mass_msun
    ms_luminosity = main_sequence_luminosity(m)
    ms_temperature = main_sequence_temperature_k(m)
    ms_lifetime = main_sequence_lifetime_years(m)
    post_ms_duration = ms_lifetime * POST_MS_FRACTION
    is_massive = m >= SUPERGIANT_MASS_THRESHOLD

    # --- Protostar: formation cutscene, mass-independent duration ---
    if age_years < FORMATION_YEARS:
        frac = age_years / FORMATION_YEARS
        temperature = 2000.0 + 1500.0 * frac
        luminosity = 1e-4 * (1 + 3 * frac)
        radius = radius_from_luminosity_temperature(luminosity, temperature) * 3
        return StellarSnapshot("protostar", radius, temperature, luminosity,
                                kelvin_to_hex(temperature), frac)

    age_ms = age_years - FORMATION_YEARS

    # --- Main sequence ---
    if age_ms < ms_lifetime:
        radius = radius_from_luminosity_temperature(ms_luminosity, ms_temperature)
        return StellarSnapshot("main_sequence", radius, ms_temperature, ms_luminosity,
                                kelvin_to_hex(ms_temperature), age_ms / ms_lifetime)

    age_post_ms = age_ms - ms_lifetime

    # --- Post-main-sequence: red giant / red supergiant ---
    if age_post_ms < post_ms_duration:
        frac = age_post_ms / post_ms_duration
        if is_massive:
            luminosity = ms_luminosity * (1 + (RED_SUPERGIANT_BRIGHTENING - 1) * frac)
            temperature = _geometric(ms_temperature, RED_SUPERGIANT_TEMPERATURE_K, frac)
        else:
            tip = _red_giant_tip_luminosity(ms_luminosity)
            luminosity = ms_luminosity + (tip - ms_luminosity) * frac
            temperature = _geometric(ms_temperature, RED_GIANT_TIP_TEMPERATURE_K, frac)
        radius = radius_from_luminosity_temperature(luminosity, temperature)
        stage = "red_supergiant" if is_massive else "red_giant"
        return StellarSnapshot(stage, radius, temperature, luminosity,
                                kelvin_to_hex(temperature), frac)

    age_terminal = age_post_ms - post_ms_duration

    # --- Terminal stages ---
    if is_massive:
        if age_terminal < TERMINAL_FLASH_YEARS:
            frac = age_terminal / TERMINAL_FLASH_YEARS
            luminosity, temperature = _supernova_light_curve(
                frac, ms_luminosity * RED_SUPERGIANT_BRIGHTENING
            )
            radius = radius_from_luminosity_temperature(luminosity, temperature)
            return StellarSnapshot("supernova", radius, temperature, luminosity,
                                    kelvin_to_hex(temperature), frac)
        if m >= BLACK_HOLE_MASS_THRESHOLD:
            return _black_hole_snapshot(m)
        return _neutron_star_snapshot()

    if age_terminal < TERMINAL_FLASH_YEARS:
        frac = age_terminal / TERMINAL_FLASH_YEARS
        tip = _red_giant_tip_luminosity(ms_luminosity)
        luminosity = tip * (1 - (1 - PLANETARY_NEBULA_FADE_FRACTION) * _smoothstep(frac, 0.6, 1.0))
        temperature = _geometric(RED_GIANT_TIP_TEMPERATURE_K, PLANETARY_NEBULA_CORE_TEMPERATURE_K, frac)
        radius = radius_from_luminosity_temperature(luminosity, temperature)
        return StellarSnapshot("planetary_nebula", radius, temperature, luminosity,
                                kelvin_to_hex(temperature), frac)

    luminosity = luminosity_from_radius_temperature(WHITE_DWARF_RADIUS_RSUN, WHITE_DWARF_TEMPERATURE_K)
    return StellarSnapshot("white_dwarf", WHITE_DWARF_RADIUS_RSUN, WHITE_DWARF_TEMPERATURE_K,
                            luminosity, kelvin_to_hex(WHITE_DWARF_TEMPERATURE_K), 1.0)


def phase_schedule(mass_msun: float) -> tuple[tuple[float, float, float], ...]:
    """The star's four timed phases as (age_start, age_end, screen_seconds):
    protostar, main sequence, post-main-sequence giant, terminal flash
    (supernova or planetary nebula). Ages are in years; screen_seconds is
    how long the phase plays at 1x, whatever its real duration."""
    ms_lifetime = main_sequence_lifetime_years(mass_msun)
    ms_start = FORMATION_YEARS
    post_ms_start = ms_start + ms_lifetime
    terminal_start = post_ms_start + ms_lifetime * POST_MS_FRACTION
    remnant_start = terminal_start + TERMINAL_FLASH_YEARS
    return (
        (0.0, ms_start, SCREEN_SECONDS_PROTOSTAR),
        (ms_start, post_ms_start, SCREEN_SECONDS_MAIN_SEQUENCE),
        (post_ms_start, terminal_start, SCREEN_SECONDS_POST_MAIN_SEQUENCE),
        (terminal_start, remnant_start, SCREEN_SECONDS_TERMINAL_FLASH),
    )


def total_screen_seconds(mass_msun: float) -> float:
    """Screen time (at 1x) from formation until the star reaches its remnant."""
    return sum(seconds for _, _, seconds in phase_schedule(mass_msun))


def cinematic_age_years(mass_msun: float, screen_seconds: float) -> float:
    """Simulated age after `screen_seconds` of playback. Piecewise-linear
    within each phase (so each phase's own animation stays smooth), with the
    per-phase screen time fixed by SCREEN_SECONDS_* rather than by how long
    the phase really lasts."""
    if screen_seconds <= 0:
        return 0.0
    schedule = phase_schedule(mass_msun)
    elapsed = 0.0
    for age_start, age_end, seconds in schedule:
        if screen_seconds < elapsed + seconds:
            return age_start + (age_end - age_start) * (screen_seconds - elapsed) / seconds
        elapsed += seconds
    # evolve()'s terminal branch is strict-`<`, so one year past the last
    # phase boundary lands squarely on the remnant.
    return schedule[-1][1] + 1.0


def evolution_track(mass_msun: float, arc_samples: int = 26) -> list[StellarSnapshot]:
    """Sample evolve() at closely-spaced ages spanning this star's full
    life, for tracing its path on an H-R diagram.

    Each phase's (T, L) formula is smooth in age-within-phase (see evolve()
    above), so this doesn't re-derive its internal timing -- it just samples
    `arc_samples` ages across each phase where the star actually moves
    (protostar, post-main-sequence, terminal flash) and a single age for
    phases that are physically static in this model (main sequence, the
    final collapsed remnant).
    """
    ms_lifetime = main_sequence_lifetime_years(mass_msun)
    post_ms_duration = ms_lifetime * POST_MS_FRACTION
    ms_start = FORMATION_YEARS
    post_ms_start = ms_start + ms_lifetime
    terminal_start = post_ms_start + post_ms_duration
    remnant_start = terminal_start + TERMINAL_FLASH_YEARS
    # evolve()'s terminal branch uses a strict `<`, so an arc sampled all
    # the way to remnant_start would land ON the remnant for its last
    # point -- stop just short so the flash's own end (frac ~= 1) is what
    # gets sampled, and the remnant stays a single, distinct final point.
    terminal_end = terminal_start + TERMINAL_FLASH_YEARS * (1 - 1e-9)

    def arc(start: float, end: float) -> list[float]:
        return [start + (end - start) * i / (arc_samples - 1) for i in range(arc_samples)]

    ages = [
        *arc(0.0, ms_start),
        ms_start,
        *arc(post_ms_start, terminal_start),
        *arc(terminal_start, terminal_end),
        remnant_start,
    ]
    return [evolve(mass_msun, age) for age in ages]
