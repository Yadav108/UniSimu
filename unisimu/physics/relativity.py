"""Light around a non-rotating (Schwarzschild) black hole (realism Phase 4).

Units: G = c = 1, so lengths are in units of the mass M. The renderer runs the
*same* ray integrator as `trace_ray` below (in GLSL); this module is its
tested twin. Equations and sources: docs/physics/equations/04-black-hole.md.
"""

import math
from dataclasses import dataclass, field

from unisimu.physics.blackbody import blackbody_display_color

# Characteristic radii, in units of M (Bruneton 2020, Section 3; Perlick &
# Tsupko 2022). Exact general-relativity results, not fitted values.
HORIZON_RADIUS_M = 2.0
PHOTON_SPHERE_RADIUS_M = 3.0
CRITICAL_IMPACT_PARAMETER_M = 3.0 * math.sqrt(3.0)  # 5.196...: the shadow's edge
ISCO_RADIUS_M = 6.0  # innermost stable circular orbit: the disc's inner edge

# "With a companion" scenario (decision D2): an isolated black hole has no
# luminous disc (Sahu et al. 2022). These are scenario parameters, labelled
# as such in the app -- not properties of any particular system.
DISK_OUTER_RADIUS_M = 20.0
DISK_PEAK_TEMPERATURE_K = 1.0e7  # ~1 keV, X-ray-binary-like; UNVERIFIED order of magnitude

# Blackbody colour table for the shader: log10 T from 3 to 8 (1000 K-10^8 K).
COLOR_TABLE_LOG_T = (3.0, 8.0)
COLOR_TABLE_SIZE = 64


def shadow_angular_radius(r_observer: float, mass: float = 1.0) -> float:
    """Angular radius (rad) of the shadow seen by a static observer at
    r_observer: sin(alpha) = 3 sqrt(3) M sqrt(1 - 2M/r) / r (Synge 1966, as
    reviewed by Perlick & Tsupko 2022, Eq. 6). Valid for r > 3M."""
    s = CRITICAL_IMPACT_PARAMETER_M * mass * math.sqrt(1.0 - 2.0 * mass / r_observer) / r_observer
    return math.asin(s)


def impact_parameter(r_observer: float, alpha: float, mass: float = 1.0) -> float:
    """b of a ray leaving a static observer at angle alpha from the outward
    radial direction: b = r sin(alpha) / sqrt(1 - 2M/r)."""
    return r_observer * math.sin(alpha) / math.sqrt(1.0 - 2.0 * mass / r_observer)


@dataclass
class RayResult:
    fate: str  # "horizon", "escape" or "undecided" (still circling after max_steps)
    escape_phi: float | None = None  # orbital angle swept until reaching infinity
    crossings: list[tuple[float, float]] = field(default_factory=list)  # (phi, r) where the ray crosses phi = phi0 + k pi


def trace_ray(
    r_observer: float,
    alpha: float,
    mass: float = 1.0,
    step: float = 0.01,
    max_steps: int = 20_000,
    plane_phi0: float | None = None,
) -> RayResult:
    """Trace a ray backward from the observer through the photon orbit
    equation u'' = 3 M u^2 - u (u = 1/r, ' = d/dphi), with RK4 in phi.

    Starts at u = 1/r_observer with u' = -u sqrt(1 - 2Mu) cot(alpha), which
    follows from (u')^2 = 1/b^2 - u^2 (1 - 2Mu) and the impact parameter
    above. If plane_phi0 is given, records where the ray passes the line
    phi = plane_phi0 + k pi (the disc plane's trace in the ray's plane).
    """
    u = 1.0 / r_observer
    w = -u * math.sqrt(1.0 - 2.0 * mass * u) * math.cos(alpha) / max(math.sin(alpha), 1e-12)
    u_horizon = 1.0 / (HORIZON_RADIUS_M * mass)
    result = RayResult("undecided")

    def accel(uu: float) -> float:
        return 3.0 * mass * uu * uu - uu

    phi = 0.0
    for _ in range(max_steps):
        k1u, k1w = w, accel(u)
        k2u, k2w = w + 0.5 * step * k1w, accel(u + 0.5 * step * k1u)
        k3u, k3w = w + 0.5 * step * k2w, accel(u + 0.5 * step * k2u)
        k4u, k4w = w + step * k3w, accel(u + step * k3u)
        u_next = u + step / 6.0 * (k1u + 2 * k2u + 2 * k3u + k4u)
        w_next = w + step / 6.0 * (k1w + 2 * k2w + 2 * k3w + k4w)
        phi_next = phi + step
        if plane_phi0 is not None:
            k = math.floor((phi_next - plane_phi0) / math.pi)
            crossing = plane_phi0 + k * math.pi
            if phi < crossing <= phi_next and k >= 0:
                f = (crossing - phi) / step
                uc = u + (u_next - u) * f
                if uc > 0:
                    result.crossings.append((crossing, 1.0 / uc))
        if u_next >= u_horizon:
            result.fate = "horizon"
            return result
        if u_next <= 0.0:
            # linear interpolation to u = 0: the direction the ray leaves along
            result.fate = "escape"
            result.escape_phi = phi + step * u / (u - u_next)
            return result
        u, w, phi = u_next, w_next, phi_next
    return result


def deflection_angle(b: float, mass: float = 1.0, step: float = 1e-3) -> float:
    """Total bending (rad) of a ray from infinity with impact parameter b > b_c:
    the angle swept minus what a straight line would sweep. Traced from a very
    distant observer, whose straight line sweeps pi - asin(b / r) rather than
    pi; weak-field limit 4M/b."""
    r_far = 1e6 * mass
    alpha = math.asin(min(b * math.sqrt(1.0 - 2.0 * mass / r_far) / r_far, 1.0))
    result = trace_ray(r_far, math.pi - alpha, mass, step=step, max_steps=10_000_000)
    if result.fate != "escape":
        raise ValueError("ray does not escape: b is inside the shadow")
    return result.escape_phi - (math.pi - math.asin(b / r_far))


def circular_orbit_redshift(r: float, lam: float, mass: float = 1.0, r_observer: float = math.inf) -> float:
    """g = nu_obs / nu_emit for gas on a circular equatorial orbit at r, seen
    along a ray with lam = L_z / E (photon's angular momentum per energy about
    the disc axis):

        g = sqrt(1 - 3M/r) / (1 - Omega lam) / sqrt(1 - 2M/r_obs),  Omega = sqrt(M / r^3)

    from the emitter 4-velocity u^t = 1/sqrt(1 - 3M/r), u^phi = Omega u^t
    (Bruneton 2020, Eqs. 13-14). The last factor is the blueshift into a
    static observer at r_obs (1 at infinity)."""
    omega = math.sqrt(mass / r**3)
    g = math.sqrt(1.0 - 3.0 * mass / r) / (1.0 - omega * lam)
    if math.isfinite(r_observer):
        g /= math.sqrt(1.0 - 2.0 * mass / r_observer)
    return g


def disk_temperature(r: float, r_inner: float, peak_temperature: float) -> float:
    """Thin-disc temperature with T^4 ~ r^-3 (1 - sqrt(r_in / r)) (Bruneton
    2020, Section 3.3.3), scaled so its maximum -- at r = 49/36 r_in -- is
    peak_temperature. 0 inside r_in."""
    if r <= r_inner:
        return 0.0

    def shape(x: float) -> float:
        return x**-3 * (1.0 - math.sqrt(r_inner / x))

    return peak_temperature * (shape(r) / shape(49.0 / 36.0 * r_inner)) ** 0.25


def bolometric_intensity_ratio(g: float) -> float:
    """I_obs / I_emit, bolometric. I_nu / nu^3 is invariant along a ray
    (Liouville), so integrating over frequency gives g^4."""
    return g**4


def blackbody_color_table() -> list[float]:
    """COLOR_TABLE_SIZE entries of (r, g, b, log10 luminance) -- the Phase 1
    blackbody colour (unit luminance) and visible luminance relative to a
    5772 K surface -- evenly spaced in log10 T. A blackbody seen with shift g
    is a blackbody at g T, so the shader only needs this one table."""
    lo, hi = COLOR_TABLE_LOG_T
    table = []
    for i in range(COLOR_TABLE_SIZE):
        temperature = 10 ** (lo + (hi - lo) * i / (COLOR_TABLE_SIZE - 1))
        color, luminance = blackbody_display_color(temperature)
        table.extend((*color, math.log10(max(luminance, 1e-30))))
    return table
