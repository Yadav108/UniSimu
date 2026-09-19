"""Coordinate mapping for the H-R diagram: log10(T)/log10(L) -> SVG pixel
space, with the astronomy-standard reversed temperature axis (hot on the
left) and a domain fitted to the current star's own track so its motion
stays legible across the full 0.1-150 M_sun range this app supports."""

import math
from functools import lru_cache

from unisimu.formatting import SUPERSCRIPT
from unisimu.physics.stellar import evolution_track

VIEW_WIDTH = 340.0
VIEW_HEIGHT = 220.0
PLOT_LEFT = 46.0
PLOT_RIGHT = VIEW_WIDTH - 12.0
PLOT_TOP = 12.0
PLOT_BOTTOM = VIEW_HEIGHT - 34.0

# Padding (in dex, i.e. log10 units) added around the star's own track so
# the curve doesn't touch the plot edges, and a floor on how tightly we'll
# zoom in even for a track that barely moves.
_DOMAIN_PAD_DEX = 0.35
_MIN_SPAN_DEX = 1.0

_T_TICK_CANDIDATES = [
    1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000,
    15000, 20000, 30000, 50000, 70000, 100000, 150000,
]
_L_TICK_CANDIDATES = [10.0**n for n in range(-6, 9)]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _padded_domain(values: list[float]) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    span = max(hi - lo, _MIN_SPAN_DEX)
    mid = (hi + lo) / 2
    lo, hi = mid - span / 2, mid + span / 2
    return lo - _DOMAIN_PAD_DEX, hi + _DOMAIN_PAD_DEX


@lru_cache(maxsize=16)
def _domain_for_mass(mass_msun: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """(log10 T domain, log10 L domain) for this star's track.

    Excludes the final (collapsed-remnant) sample from the fit: a white
    dwarf/neutron star/black hole sits many decades outside the normal H-R
    range in this simplified model, and letting it set the scale would
    flatten the star's actual (interesting) life track to a sliver. The
    remnant point is still plotted -- just clamped into this domain, which
    reads as the marker settling into a corner once the star collapses.
    """
    track = evolution_track(mass_msun)[:-1]
    log_t = [math.log10(max(s.temperature_k, 1e-3)) for s in track]
    log_l = [math.log10(max(s.luminosity_lsun, 1e-12)) for s in track]
    return _padded_domain(log_t), _padded_domain(log_l)


def _t_to_x(log_t: float, t_domain: tuple[float, float]) -> float:
    t_lo, t_hi = t_domain
    x = PLOT_LEFT + (t_hi - log_t) / (t_hi - t_lo) * (PLOT_RIGHT - PLOT_LEFT)
    return _clamp(x, PLOT_LEFT, PLOT_RIGHT)


def _l_to_y(log_l: float, l_domain: tuple[float, float]) -> float:
    l_lo, l_hi = l_domain
    y = PLOT_BOTTOM - (log_l - l_lo) / (l_hi - l_lo) * (PLOT_BOTTOM - PLOT_TOP)
    return _clamp(y, PLOT_TOP, PLOT_BOTTOM)


def _to_screen(
    temperature_k: float,
    luminosity_lsun: float,
    t_domain: tuple[float, float],
    l_domain: tuple[float, float],
) -> tuple[float, float]:
    log_t = math.log10(max(temperature_k, 1e-3))
    log_l = math.log10(max(luminosity_lsun, 1e-12))
    return _t_to_x(log_t, t_domain), _l_to_y(log_l, l_domain)


def _axis_ticks(candidates: list[float], domain: tuple[float, float], max_ticks: int = 6) -> list[float]:
    lo, hi = domain
    in_range = [v for v in candidates if lo - 1e-9 <= math.log10(v) <= hi + 1e-9]
    if len(in_range) <= max_ticks:
        return in_range
    step = math.ceil(len(in_range) / max_ticks)
    return in_range[::step]


def _luminosity_label(value: float) -> str:
    n = round(math.log10(value))
    return "1" if n == 0 else f"10{str(n).translate(SUPERSCRIPT)}"


def track_polyline(mass_msun: float) -> str:
    """SVG `points` string for this star's full evolutionary track."""
    t_domain, l_domain = _domain_for_mass(mass_msun)
    points = (
        _to_screen(s.temperature_k, s.luminosity_lsun, t_domain, l_domain)
        for s in evolution_track(mass_msun)
    )
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def marker_position(mass_msun: float, temperature_k: float, luminosity_lsun: float) -> list[float]:
    """Live SVG [x, y] for the star's current position on its track."""
    t_domain, l_domain = _domain_for_mass(mass_msun)
    x, y = _to_screen(temperature_k, luminosity_lsun, t_domain, l_domain)
    return [x, y]


def temperature_ticks(mass_msun: float) -> list[tuple[float, str]]:
    """(screen x, label) pairs for the temperature axis gridlines."""
    t_domain, _ = _domain_for_mass(mass_msun)
    return [
        (_t_to_x(math.log10(v), t_domain), f"{v:,.0f}")
        for v in _axis_ticks(_T_TICK_CANDIDATES, t_domain)
    ]


def luminosity_ticks(mass_msun: float) -> list[tuple[float, str]]:
    """(screen y, label) pairs for the luminosity axis gridlines."""
    _, l_domain = _domain_for_mass(mass_msun)
    return [
        (_l_to_y(math.log10(v), l_domain), _luminosity_label(v))
        for v in _axis_ticks(_L_TICK_CANDIDATES, l_domain)
    ]
