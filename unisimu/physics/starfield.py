"""Background-star physics for the catalogue starfield (realism Phase 2).

Equations and sources: docs/physics/equations/02-starfield.md.
"""

import math

# Scene axes: the celestial (J2000 equatorial) frame with the north celestial
# pole pointing up. Equatorial (x, y, z) -- +x to the vernal equinox, +z to the
# north pole -- maps to three.js (X, Y, Z) = (x, z, -y), which keeps the frame
# right-handed so the sky is not mirrored.


def bv_to_temperature(bv: float) -> float:
    """Blackbody temperature (K) from the B-V colour index.

    Ballesteros (2012), EPL 97, 34008, Eq. 14:
    T = 4600 (1 / (0.92 (B-V) + 1.7) + 1 / (0.92 (B-V) + 0.62)).
    A blackbody approximation, not a fit to stellar atmospheres.
    """
    return 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62))


def relative_flux(magnitude: float, reference_magnitude: float = 0.0) -> float:
    """Flux relative to a star of `reference_magnitude` in the same band
    (Pogson: f / f_ref = 10^(-0.4 (m - m_ref)))."""
    return 10.0 ** (-0.4 * (magnitude - reference_magnitude))


def equatorial_unit_vector(ra_rad: float, dec_rad: float) -> tuple[float, float, float]:
    """Unit vector toward (RA, Dec) in the equatorial frame."""
    cos_dec = math.cos(dec_rad)
    return (cos_dec * math.cos(ra_rad), cos_dec * math.sin(ra_rad), math.sin(dec_rad))


def equatorial_to_scene(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Equatorial (x, y, z) -> scene (X, Y, Z) with the celestial pole up."""
    return (x, z, -y)


def scene_direction(ra_rad: float, dec_rad: float) -> tuple[float, float, float]:
    return equatorial_to_scene(*equatorial_unit_vector(ra_rad, dec_rad))
