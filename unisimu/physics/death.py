"""How stars die, as an observer would see it (realism Phase 5): a Type II-P
supernova light curve, a planetary nebula's emission-line colour and growth.

A simplified model, not radiative transfer. Equations and sources:
docs/physics/equations/05-death-scenes.md and docs/physics/05-death-scenes.md.
"""

import math
from bisect import bisect_right

from unisimu.physics.blackbody import LINEAR_SRGB_TO_XYZ, cie1931_cmf, xyz_to_linear_srgb

SECONDS_PER_DAY = 86_400.0
DAYS_PER_YEAR = 365.25
SOLAR_LUMINOSITY_ERG_S = 3.828e33  # IAU 2015 B3 nominal, in erg/s
SOLAR_MASS_G = 1.988_409_9e33  # (GM)_sun nominal / CODATA G, in grams

# --- Type II-P supernova -------------------------------------------------
# How long the light curve shown on screen covers: the plateau (~100 d), its
# drop, and the start of the radioactive tail.
SUPERNOVA_LIGHT_CURVE_DAYS = 400.0

# Shock breakout: about a day after core bounce (Vartanyan et al. 2025, 3D
# model of a 17 M_sun RSG). Before it nothing changes at the surface.
SHOCK_BREAKOUT_DAY = 1.0
# The breakout flash itself is ILLUSTRATIVE: these two numbers are not from a
# source, only chosen to give a short, hot, bright flash.
BREAKOUT_PEAK_DAY = 1.2
BREAKOUT_PEAK_TEMPERATURE_K = 3.0e4
BREAKOUT_PEAK_LUMINOSITY_LSUN = 2.0e9

# Photosphere of the s15e12 model (15 M_sun RSG, 1.2 B explosion), Dessart &
# Hillier (2011), MNRAS, arXiv:1008.3238, Table 4: (day, T_phot [K],
# L_bol [10^8 L_sun]). The photosphere disappears after 143 d.
DESSART_S15E12 = (
    (9.3, 10661, 7.94), (10.2, 10063, 7.64), (11.2, 9527, 7.54), (12.3, 9057, 7.50),
    (13.5, 8642, 7.44), (14.8, 8317, 7.37), (16.3, 8054, 7.24), (17.9, 7859, 7.11),
    (19.7, 7678, 6.96), (21.7, 7477, 6.78), (23.9, 7208, 6.65), (26.3, 6878, 6.56),
    (28.9, 6564, 6.49), (31.8, 6305, 6.42), (35.0, 6087, 6.35), (38.5, 5893, 6.30),
    (42.4, 5735, 6.29), (46.6, 5478, 6.19), (51.3, 5403, 6.19), (56.5, 5355, 6.15),
    (62.1, 5306, 6.03), (68.3, 5255, 5.85), (75.1, 5211, 5.61), (82.6, 5174, 5.32),
    (90.0, 5162, 5.02), (99.0, 5185, 4.52), (108.0, 5276, 3.98), (118.0, 5415, 3.31),
    (130.0, 5775, 2.18), (143.0, 5550, 1.11),
)
# The same model's 56Ni mass (Dessart & Hillier 2011, Fig. 9): powers the tail.
NICKEL_MASS_MSUN = 0.0866
# Blend from the last photospheric point onto the decay curve over this long.
TAIL_BLEND_DAYS = 20.0

# 56Ni -> 56Co -> 56Fe energy deposition (Nadyozhin 1994, as quoted by Yao et
# al. 2020, Eqs. B4-B6), full gamma-ray trapping. Lifetimes agree with NNDC
# half-lives 6.075 d and 77.236 d.
NICKEL_HEATING_ERG_G_S = 3.90e10
COBALT_HEATING_ERG_G_S = 6.78e9
NICKEL_LIFETIME_DAYS = 8.8
COBALT_LIFETIME_DAYS = 111.3


def radioactive_luminosity_lsun(t_days: float, nickel_mass_msun: float = NICKEL_MASS_MSUN) -> float:
    """Decay-powered luminosity: M_Ni [eps_Ni e^(-t/tau_Ni) + eps_Co (e^(-t/tau_Co) - e^(-t/tau_Ni))]."""
    ni = math.exp(-t_days / NICKEL_LIFETIME_DAYS)
    co = math.exp(-t_days / COBALT_LIFETIME_DAYS)
    heating = NICKEL_HEATING_ERG_G_S * ni + COBALT_HEATING_ERG_G_S * (co - ni)
    return nickel_mass_msun * SOLAR_MASS_G * heating / SOLAR_LUMINOSITY_ERG_S


def _log_lerp(a: float, b: float, t: float) -> float:
    return math.exp(math.log(a) + (math.log(b) - math.log(a)) * t)


def _photosphere(t_days: float) -> tuple[float, float]:
    """(L [L_sun], T [K]) interpolated in the s15e12 table: log L, linear T."""
    days = [row[0] for row in DESSART_S15E12]
    i = min(max(bisect_right(days, t_days) - 1, 0), len(days) - 2)
    d0, t0, l0 = DESSART_S15E12[i]
    d1, t1, l1 = DESSART_S15E12[i + 1]
    f = min(max((t_days - d0) / (d1 - d0), 0.0), 1.0)
    return _log_lerp(l0 * 1e8, l1 * 1e8, f), t0 + (t1 - t0) * f


def supernova_state(
    t_days: float, progenitor_luminosity_lsun: float, progenitor_temperature_k: float
) -> tuple[float, float]:
    """(luminosity [L_sun], effective temperature [K]) `t_days` after core
    collapse. The radius follows from Stefan-Boltzmann, as for every stage.

    Before breakout the progenitor is unchanged; then a short illustrative
    flash; then the s15e12 photosphere (plateau and drop); then, once the
    photosphere is gone, the 56Ni/56Co decay tail. After the photosphere
    disappears there is no single temperature -- the last photospheric value
    is kept for colour, and that is a simplification.
    """
    if t_days < SHOCK_BREAKOUT_DAY:
        return progenitor_luminosity_lsun, progenitor_temperature_k
    first_day, first_t, first_l = DESSART_S15E12[0]
    if t_days < BREAKOUT_PEAK_DAY:
        f = (t_days - SHOCK_BREAKOUT_DAY) / (BREAKOUT_PEAK_DAY - SHOCK_BREAKOUT_DAY)
        return (
            _log_lerp(progenitor_luminosity_lsun, BREAKOUT_PEAK_LUMINOSITY_LSUN, f),
            _log_lerp(progenitor_temperature_k, BREAKOUT_PEAK_TEMPERATURE_K, f),
        )
    if t_days < first_day:
        f = (t_days - BREAKOUT_PEAK_DAY) / (first_day - BREAKOUT_PEAK_DAY)
        return (
            _log_lerp(BREAKOUT_PEAK_LUMINOSITY_LSUN, first_l * 1e8, f),
            _log_lerp(BREAKOUT_PEAK_TEMPERATURE_K, first_t, f),
        )
    last_day, last_t, last_l = DESSART_S15E12[-1]
    if t_days <= last_day:
        return _photosphere(t_days)
    tail = radioactive_luminosity_lsun(t_days)
    if t_days < last_day + TAIL_BLEND_DAYS:
        f = (t_days - last_day) / TAIL_BLEND_DAYS
        return _log_lerp(last_l * 1e8, tail, f), last_t
    return tail, last_t


# --- Planetary nebula ------------------------------------------------------
# True expansion of the outer edge, and visibility time to R = 0.9 pc
# (Jacob, Schoenberner & Steffen 2013, A&A, arXiv:1307.6189).
PLANETARY_NEBULA_EXPANSION_KM_S = 42.0
PLANETARY_NEBULA_VISIBLE_YEARS = 21_000.0
KM_PER_PARSEC = 3.085_677_581e13

# Integrated emission lines of NGC 7009, relative to H-beta (Phillips, Cuesta &
# Ramos-Larios 2010, arXiv:1008.4178, envelope total): wavelength [nm], ratio.
# One representative nebula; others differ (e.g. far stronger [N II]).
PLANETARY_NEBULA_LINES = (
    (486.1327, 1.00),  # H-beta
    (495.8915, 3.60),  # [O III]
    (500.6845, 10.9),  # [O III]
    (656.2804, 2.79),  # H-alpha
    (658.3467, 0.126),  # [N II]
)


def planetary_nebula_radius_pc(years_since_ejection: float) -> float:
    return PLANETARY_NEBULA_EXPANSION_KM_S * years_since_ejection * DAYS_PER_YEAR * SECONDS_PER_DAY / KM_PER_PARSEC


def emission_line_color(lines=PLANETARY_NEBULA_LINES) -> tuple[float, float, float]:
    """Linear sRGB colour (luminance 1) of a spectrum of narrow emission lines:
    the CIE response at each line, weighted by its strength. Out-of-gamut
    channels (pure line colours often are) are clipped after normalising."""
    xyz = [0.0, 0.0, 0.0]
    for wavelength_nm, strength in lines:
        for i, c in enumerate(cie1931_cmf(wavelength_nm)):
            xyz[i] += strength * c
    rgb = xyz_to_linear_srgb(tuple(v / xyz[1] for v in xyz))
    luminance = sum(LINEAR_SRGB_TO_XYZ[1][c] * v for c, v in enumerate(rgb))
    return tuple(max(v, 0.0) / luminance for v in rgb)
