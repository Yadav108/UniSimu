"""Approximate blackbody radiation color as a function of temperature.

Uses the Tanner Helland piecewise-polynomial fit to Mitchell Charity's
blackbody data, valid over roughly 1000K-40000K (the full range our
stellar stages span, from cool protostars/remnants to supernova flashes).
"""

import math


def _clamp(value: float, lo: float = 0.0, hi: float = 255.0) -> float:
    return max(lo, min(hi, value))


def kelvin_to_rgb(temperature_k: float) -> tuple[int, int, int]:
    temp = _clamp(temperature_k, 1000.0, 40000.0) / 100.0

    if temp <= 66:
        red = 255.0
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
        red = _clamp(red)

    if temp <= 66:
        green = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    green = _clamp(green)

    if temp >= 66:
        blue = 255.0
    elif temp <= 19:
        blue = 0.0
    else:
        blue = 138.5177312231 * math.log(temp - 10) - 305.0447927307
        blue = _clamp(blue)

    return (round(red), round(green), round(blue))


def kelvin_to_hex(temperature_k: float) -> str:
    r, g, b = kelvin_to_rgb(temperature_k)
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------
# Physically based colour (realism Phase 1). The fit above stays as-is for the
# stylized look; the functions below go spectrum -> CIE XYZ -> linear sRGB and
# keep brightness, so they can feed an HDR pipeline. Equations and sources:
# docs/physics/equations/01-radiometry-color.md.

PLANCK_H = 6.626_070_15e-34  # J s, exact (CODATA 2022)
LIGHT_C = 299_792_458.0  # m/s, exact
BOLTZMANN_K = 1.380_649e-23  # J/K, exact
# IAU 2015 Resolution B3 nominal solar effective temperature. Used only as the
# brightness reference (luminance 1); stellar.py keeps its own 5778 K constant.
REFERENCE_TEMPERATURE_K = 5772.0

_WAVELENGTHS_NM = range(360, 831)  # visible range at 1 nm steps
_D_LAMBDA_M = 1e-9


def planck_spectral_radiance(wavelength_m: float, temperature_k: float) -> float:
    """B_lambda(lambda, T) in W sr^-1 m^-3."""
    if temperature_k <= 0:
        return 0.0
    x = PLANCK_H * LIGHT_C / (wavelength_m * BOLTZMANN_K * temperature_k)
    if x > 700:  # exp would overflow; the radiance is ~0 anyway
        return 0.0
    return 2 * PLANCK_H * LIGHT_C**2 / wavelength_m**5 / math.expm1(x)


def _lobe(wavelength_nm: float, mean: float, inv_width_lo: float, inv_width_hi: float) -> float:
    t = (wavelength_nm - mean) * (inv_width_lo if wavelength_nm < mean else inv_width_hi)
    return math.exp(-0.5 * t * t)


def cie1931_cmf(wavelength_nm: float) -> tuple[float, float, float]:
    """CIE 1931 2-degree colour-matching functions (x-bar, y-bar, z-bar), using
    the multi-lobe fit of Wyman, Sloan & Shirley, JCGT 2(2) 2013, Eq. 4."""
    w = wavelength_nm
    x = (
        0.362 * _lobe(w, 442.0, 0.0624, 0.0374)
        + 1.056 * _lobe(w, 599.8, 0.0264, 0.0323)
        - 0.065 * _lobe(w, 501.1, 0.0490, 0.0382)
    )
    y = 0.821 * _lobe(w, 568.8, 0.0213, 0.0247) + 0.286 * _lobe(w, 530.9, 0.0613, 0.0322)
    z = 1.217 * _lobe(w, 437.0, 0.0845, 0.0278) + 0.681 * _lobe(w, 459.0, 0.0385, 0.0725)
    return (x, y, z)


_CMF_TABLE = tuple((w * 1e-9, cie1931_cmf(w)) for w in _WAVELENGTHS_NM)


def blackbody_xyz(temperature_k: float) -> tuple[float, float, float]:
    """Unnormalised CIE XYZ of a blackbody: the integral of B_lambda times each
    colour-matching function over 360-830 nm."""
    X = Y = Z = 0.0
    for wavelength_m, (xb, yb, zb) in _CMF_TABLE:
        b = planck_spectral_radiance(wavelength_m, temperature_k)
        X += b * xb
        Y += b * yb
        Z += b * zb
    return (X * _D_LAMBDA_M, Y * _D_LAMBDA_M, Z * _D_LAMBDA_M)


def chromaticity(temperature_k: float) -> tuple[float, float]:
    """CIE 1931 (x, y) chromaticity of a blackbody (a point on the Planckian locus)."""
    X, Y, Z = blackbody_xyz(temperature_k)
    total = X + Y + Z
    if total <= 0:
        raise ValueError("chromaticity is undefined for a body with no visible emission")
    return (X / total, Y / total)


def _srgb_xyz_matrices() -> tuple[tuple[tuple[float, ...], ...], tuple[tuple[float, ...], ...]]:
    """Linear-sRGB <-> XYZ matrices built from the sRGB primaries and D65 white
    point (ICC sRGB registry), rather than typing in 18 magic numbers."""
    primaries = ((0.64, 0.33), (0.30, 0.60), (0.15, 0.06))
    white = (0.3127, 0.3290)

    def xyz_at_unit_y(x: float, y: float) -> tuple[float, float, float]:
        return (x / y, 1.0, (1 - x - y) / y)

    cols = [xyz_at_unit_y(*p) for p in primaries]
    m = [[cols[c][r] for c in range(3)] for r in range(3)]
    m_inv = _inverse3(m)
    w = xyz_at_unit_y(*white)
    scale = [sum(m_inv[r][c] * w[c] for c in range(3)) for r in range(3)]
    rgb_to_xyz = tuple(tuple(m[r][c] * scale[c] for c in range(3)) for r in range(3))
    xyz_to_rgb = tuple(tuple(row) for row in _inverse3(rgb_to_xyz))
    return rgb_to_xyz, xyz_to_rgb


def _inverse3(m) -> list[list[float]]:
    (a, b, c), (d, e, f), (g, h, i) = m
    co_a, co_b, co_c = e * i - f * h, -(d * i - f * g), d * h - e * g
    det = a * co_a + b * co_b + c * co_c
    return [
        [co_a / det, -(b * i - c * h) / det, (b * f - c * e) / det],
        [co_b / det, (a * i - c * g) / det, -(a * f - c * d) / det],
        [co_c / det, -(a * h - b * g) / det, (a * e - b * d) / det],
    ]


LINEAR_SRGB_TO_XYZ, XYZ_TO_LINEAR_SRGB = _srgb_xyz_matrices()
_REFERENCE_Y = blackbody_xyz(REFERENCE_TEMPERATURE_K)[1]


def xyz_to_linear_srgb(xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(XYZ_TO_LINEAR_SRGB[r][c] * xyz[c] for c in range(3)) for r in range(3))


def blackbody_linear_rgb(temperature_k: float) -> tuple[float, float, float]:
    """Linear sRGB of a blackbody's surface, in units where a 5772 K surface
    has luminance Y = 1. Brightness is kept (a hotter surface is brighter, per
    unit area), and very cool bodies may have a slightly negative channel
    (outside the sRGB gamut); clip for display, not here."""
    X, Y, Z = blackbody_xyz(temperature_k)
    return xyz_to_linear_srgb((X / _REFERENCE_Y, Y / _REFERENCE_Y, Z / _REFERENCE_Y))


def blackbody_display_color(temperature_k: float) -> tuple[tuple[float, float, float], float]:
    """Split a blackbody's linear sRGB into (colour with luminance 1, luminance).

    The colour has negative channels clipped to 0 after the luminance is taken.
    The luminance is relative to a 5772 K surface: the camera-visible surface
    brightness the renderer multiplies by its exposure."""
    r, g, b = blackbody_linear_rgb(temperature_k)
    luminance = sum(LINEAR_SRGB_TO_XYZ[1][c] * v for c, v in enumerate((r, g, b)))
    if luminance <= 0:
        return (0.0, 0.0, 0.0), 0.0
    unit = tuple(max(v, 0.0) / luminance for v in (r, g, b))
    return unit, luminance
