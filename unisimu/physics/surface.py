"""What a star's visible surface looks like: limb darkening, granulation,
starspot contrast, pulsation period (realism Phase 3).

Equations and sources: docs/physics/equations/03-stellar-surface.md.
"""

import math
from bisect import bisect_right

from unisimu.physics import limb_darkening_data as ld
from unisimu.physics.blackbody import BOLTZMANN_K, blackbody_linear_rgb

# IAU 2015 Resolution B3 nominal solar values (exact by definition)
SOLAR_RADIUS_M = 6.957e8
SOLAR_GM_M3_S2 = 1.327_124_4e20
ATOMIC_MASS_UNIT_KG = 1.660_539_068_92e-27  # CODATA 2022
# Mean molecular weight of a neutral solar-mix photosphere, in atomic mass
# units. An assumption (documented), not a fitted value.
PHOTOSPHERE_MEAN_MOLECULAR_WEIGHT = 1.3

# Granule diameter in pressure scale heights: about 4 for dwarfs (Magic et al.
# 2013, "Nordlund scaling relation", d = 4 (v_h / v_z) H_P), about 15 for red
# giants (Mathur et al. 2011). Interpolated in log g between those regimes.
GRANULE_SIZE_HP_DWARF = 4.0
GRANULE_SIZE_HP_GIANT = 15.0
DWARF_LOGG = 4.4
GIANT_LOGG = 2.5

# Bolometric granulation intensity contrast I_rms for the Sun's 3D model
# (Magic et al. 2013: 15 %). Since I ~ T^4, the temperature contrast is a quarter.
GRANULATION_TEMPERATURE_CONTRAST = 0.15 / 4.0

# Surface convection fades out on the upper main sequence: H convection becomes
# largely inefficient above ~8250 K and surfaces are radiative by 9000-10000 K
# (Cantiello & Braithwaite 2019). No granulation is drawn above the upper value.
GRANULATION_FADE_START_K = 8250.0
GRANULATION_FADE_END_K = 10000.0

# Sunspot umbrae: 3900-4800 K against a 5772 K photosphere (Solanki 2003, as
# quoted by Murphy et al. 2026). The midpoint ratio is applied to every star --
# an assumption, since spots on other stars are poorly constrained.
SPOT_TEMPERATURE_RATIO = ((3900.0 + 4800.0) / 2.0) / 5772.0

# Fundamental-mode pulsation constant for red supergiants, Q = P (M/M_sun)^(1/2)
# (R/R_sun)^(-3/2) = 0.085 +- 0.02 d (Kiss, Szabo & Bedding 2006).
PULSATION_Q_DAYS = 0.085


def surface_gravity_cgs(mass_msun: float, radius_rsun: float) -> float:
    """log10 of surface gravity g = GM / R^2, in cm s^-2 (the astronomers' log g)."""
    g_si = SOLAR_GM_M3_S2 * mass_msun / (radius_rsun * SOLAR_RADIUS_M) ** 2
    return math.log10(g_si * 100.0)


def pressure_scale_height_m(temperature_k: float, mass_msun: float, radius_rsun: float) -> float:
    """H_p = k_B T / (mu m_u g)."""
    g_si = SOLAR_GM_M3_S2 * mass_msun / (radius_rsun * SOLAR_RADIUS_M) ** 2
    return BOLTZMANN_K * temperature_k / (PHOTOSPHERE_MEAN_MOLECULAR_WEIGHT * ATOMIC_MASS_UNIT_KG * g_si)


def granule_size_in_scale_heights(logg: float) -> float:
    t = (DWARF_LOGG - logg) / (DWARF_LOGG - GIANT_LOGG)
    t = min(max(t, 0.0), 1.0)
    return GRANULE_SIZE_HP_DWARF + t * (GRANULE_SIZE_HP_GIANT - GRANULE_SIZE_HP_DWARF)


def granule_diameter_m(temperature_k: float, mass_msun: float, radius_rsun: float) -> float:
    logg = surface_gravity_cgs(mass_msun, radius_rsun)
    return granule_size_in_scale_heights(logg) * pressure_scale_height_m(temperature_k, mass_msun, radius_rsun)


def granulation_scale(temperature_k: float, mass_msun: float, radius_rsun: float) -> float:
    """Number of granules around the star's circumference (2 pi R / d)."""
    return 2 * math.pi * radius_rsun * SOLAR_RADIUS_M / granule_diameter_m(temperature_k, mass_msun, radius_rsun)


def granulation_visibility(temperature_k: float) -> float:
    """1 for convective surfaces, fading to 0 across the radiative transition."""
    t = (temperature_k - GRANULATION_FADE_START_K) / (GRANULATION_FADE_END_K - GRANULATION_FADE_START_K)
    return 1.0 - min(max(t, 0.0), 1.0)


def _channel_ratio(hot: tuple[float, ...], cool: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(max(c, 0.0) / h if h > 0 else 0.0 for h, c in zip(hot, cool))


def spot_contrast(temperature_k: float) -> tuple[float, float, float]:
    """Per-channel intensity of a starspot umbra relative to the photosphere,
    straight from the Planck law at the two temperatures."""
    if temperature_k <= 0:
        return (1.0, 1.0, 1.0)
    return _channel_ratio(
        blackbody_linear_rgb(temperature_k), blackbody_linear_rgb(temperature_k * SPOT_TEMPERATURE_RATIO)
    )


def temperature_sensitivity(temperature_k: float) -> tuple[float, float, float]:
    """d ln I / d ln T per channel: how strongly each colour channel responds
    to a small temperature change (blue responds more for a cool star)."""
    if temperature_k <= 0:
        return (0.0, 0.0, 0.0)
    h = 0.01
    hot = blackbody_linear_rgb(temperature_k * (1 + h))
    cold = blackbody_linear_rgb(temperature_k * (1 - h))
    mid = blackbody_linear_rgb(temperature_k)
    return tuple((a - b) / (2 * h * m) if m > 0 else 0.0 for a, b, m in zip(hot, cold, mid))


def _bracket(grid: tuple[float, ...], value: float) -> tuple[int, int, float]:
    value = min(max(value, grid[0]), grid[-1])
    i = min(bisect_right(grid, value) - 1, len(grid) - 2)
    t = (value - grid[i]) / (grid[i + 1] - grid[i])
    return i, i + 1, t


def limb_darkening(temperature_k: float, logg: float) -> tuple[float, ...]:
    """Quadratic-law coefficients (a_R, a_G, a_B, b_R, b_G, b_B) for
    I(mu)/I(1) = 1 - a (1 - mu) - b (1 - mu)^2, bilinear in (Teff, log g)
    over the Claret & Bloemen (2011) grid, clamped at its edges
    (3500-50000 K, log g 0-5)."""
    i0, i1, ti = _bracket(ld.TEFF_K, temperature_k)
    j0, j1, tj = _bracket(ld.LOGG_CGS, logg)
    c = ld.COEFFS
    return tuple(
        (1 - ti) * (1 - tj) * c[i0][j0][k]
        + ti * (1 - tj) * c[i1][j0][k]
        + (1 - ti) * tj * c[i0][j1][k]
        + ti * tj * c[i1][j1][k]
        for k in range(6)
    )


def pulsation_period_days(mass_msun: float, radius_rsun: float) -> float:
    """Fundamental radial pulsation period P = Q sqrt(R^3 / M) in days."""
    return PULSATION_Q_DAYS * radius_rsun**1.5 / math.sqrt(mass_msun)
