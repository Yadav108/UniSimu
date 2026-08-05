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
"""

import math
from dataclasses import dataclass

from unisimu.physics.blackbody import kelvin_to_hex

SUN_TEMPERATURE_K = 5778.0

FORMATION_YEARS = 5.0e4
POST_MS_FRACTION = 0.10
TERMINAL_FLASH_YEARS = 2.0e3

SUPERGIANT_MASS_THRESHOLD = 8.0
BLACK_HOLE_MASS_THRESHOLD = 20.0

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
    return SUN_TEMPERATURE_K * mass_msun**0.54


def radius_from_luminosity_temperature(luminosity_lsun: float, temperature_k: float) -> float:
    """Stefan-Boltzmann: L = 4*pi*R^2*sigma*T^4 => R/Rsun = sqrt(L/Lsun) * (Tsun/T)^2."""
    l = max(luminosity_lsun, 1e-6)
    return math.sqrt(l) * (SUN_TEMPERATURE_K / temperature_k) ** 2


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
        luminosity = ms_luminosity * (1 + 100 * frac)
        temperature = max(3000.0, ms_temperature * (1 - 0.6 * frac))
        radius = radius_from_luminosity_temperature(luminosity, temperature)
        stage = "red_supergiant" if is_massive else "red_giant"
        return StellarSnapshot(stage, radius, temperature, luminosity,
                                kelvin_to_hex(temperature), frac)

    age_terminal = age_post_ms - post_ms_duration

    # --- Terminal stages ---
    if is_massive:
        if age_terminal < TERMINAL_FLASH_YEARS:
            frac = age_terminal / TERMINAL_FLASH_YEARS
            temperature = 20000.0 + 30000.0 * (1 - frac)
            luminosity = ms_luminosity * 1e4 * (1 - frac) + 1
            radius = 20.0 * (1 - frac) + 0.5
            return StellarSnapshot("supernova", radius, temperature, luminosity,
                                    kelvin_to_hex(temperature), frac)
        remnant_stage = "black_hole" if m >= BLACK_HOLE_MASS_THRESHOLD else "neutron_star"
        remnant_radius = 0.0 if remnant_stage == "black_hole" else 0.00003
        return StellarSnapshot(remnant_stage, remnant_radius, 50.0, 1e-6, "#111111", 1.0)

    if age_terminal < TERMINAL_FLASH_YEARS:
        frac = age_terminal / TERMINAL_FLASH_YEARS
        temperature = 15000.0
        luminosity = ms_luminosity * 0.3
        radius = 5.0 * (1 - frac) + 0.02
        return StellarSnapshot("planetary_nebula", radius, temperature, luminosity,
                                kelvin_to_hex(temperature), frac)

    temperature = 15000.0
    return StellarSnapshot("white_dwarf", 0.01, temperature, 0.001,
                            kelvin_to_hex(temperature), 1.0)
