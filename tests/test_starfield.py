"""Tests for the catalogue starfield (realism Phase 2): the physics helpers,
the build tool on a tiny synthetic catalogue, and the shipped binary."""

import math
from pathlib import Path

import pytest

from tools.build_starfield import build, parse
from unisimu.physics.starfield import (
    bv_to_temperature,
    equatorial_to_scene,
    relative_flux,
    scene_direction,
)

BINARY = Path(__file__).resolve().parents[1] / "assets" / "starfield.bin"


@pytest.mark.parametrize(
    "bv,temperature",
    # Ballesteros 2012 Eq. 14, values tabulated in docs/physics/equations/02-starfield.md
    [(-0.3, 16602), (0.0, 10125), (0.65, 5778), (1.0, 4743), (1.5, 3794), (2.0, 3169)],
)
def test_bv_to_temperature_matches_reference_table(bv, temperature):
    assert bv_to_temperature(bv) == pytest.approx(temperature, abs=1.0)


def test_bv_to_temperature_decreases_with_redder_colour():
    temps = [bv_to_temperature(bv / 10) for bv in range(-4, 21)]
    assert all(a > b for a, b in zip(temps, temps[1:]))


def test_five_magnitudes_is_a_factor_of_one_hundred():
    assert relative_flux(0.0) / relative_flux(5.0) == pytest.approx(100.0)
    assert relative_flux(1.0, reference_magnitude=1.0) == 1.0


def test_scene_axes_put_the_celestial_pole_up():
    assert scene_direction(0.0, math.pi / 2) == pytest.approx((0.0, 1.0, 0.0), abs=1e-12)
    # RA 0h on the equator is the vernal equinox: scene +X
    assert scene_direction(0.0, 0.0) == pytest.approx((1.0, 0.0, 0.0), abs=1e-12)
    # RA 6h on the equator: equatorial +y -> scene -Z
    assert scene_direction(math.pi / 2, 0.0) == pytest.approx((0.0, 0.0, -1.0), abs=1e-12)


def test_scene_frame_is_right_handed_not_mirrored():
    ex, ey, ez = (equatorial_to_scene(*v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    cross = (ex[1] * ey[2] - ex[2] * ey[1], ex[2] * ey[0] - ex[0] * ey[2], ex[0] * ey[1] - ex[1] * ey[0])
    assert cross == pytest.approx(ez)


def _synthetic_rows():
    # (ra_rad, dec_rad, mag, ci) -- like read_catalogue's output (the Sun is
    # filtered out by read_catalogue itself)
    return [
        (1.7678, math.radians(-16.716), -1.44, "0.009"),  # Sirius
        (1.6753, math.radians(-52.696), -0.62, "0.164"),  # Canopus
        (0.5, 0.2, 6.0, ""),  # missing colour index
        (2.0, -0.3, 8.0, "1.2"),  # fainter than the cut: glow only
        (3.0, 0.1, 12.0, "0.5"),  # fainter than the glow limit: dropped
    ]


def test_build_sorts_brightest_first_and_splits_stars_from_glow():
    info = parse(build(_synthetic_rows()))
    stars = info["stars"]
    assert len(stars) == 3
    fluxes = [s[6] for s in stars]
    assert fluxes == sorted(fluxes, reverse=True)
    assert fluxes[0] == pytest.approx(relative_flux(-1.44), rel=1e-6)
    total_glow = sum(info["glow"])
    assert total_glow > 0  # the mag-8 star landed in the glow map


def test_build_directions_are_unit_vectors_and_colours_unit_luminance():
    for x, y, z, r, g, b, _ in parse(build(_synthetic_rows()))["stars"]:
        assert math.hypot(x, y, z) == pytest.approx(1.0, abs=1e-6)
        assert 0.2126 * r + 0.7152 * g + 0.0722 * b == pytest.approx(1.0, abs=1e-5)


def test_missing_colour_index_gets_neutral_colour():
    faint = parse(build(_synthetic_rows()))["stars"][2]
    r, g, b = faint[3:6]
    assert min(r, g, b) / max(r, g, b) > 0.8  # 5772 K: near white


def test_glow_map_conserves_flux():
    # Sum over the sky of brightness x solid angle = total flux of glow stars.
    info = parse(build(_synthetic_rows()))
    w, h, glow = info["glow_w"], info["glow_h"], info["glow"]
    d_ra = 2 * math.pi / w
    total = 0.0
    for row in range(h):
        dec_top = math.pi / 2 - row * math.pi / h
        omega = d_ra * (math.sin(dec_top) - math.sin(dec_top - math.pi / h))
        for col in range(w):
            i = 3 * (row * w + col)
            total += (0.2126 * glow[i] + 0.7152 * glow[i + 1] + 0.0722 * glow[i + 2]) * omega
    assert total == pytest.approx(relative_flux(8.0), rel=1e-4)


@pytest.mark.skipif(not BINARY.exists(), reason="assets/starfield.bin not built")
def test_shipped_binary_has_sirius_then_canopus():
    info = parse(BINARY.read_bytes())
    sirius, canopus = info["stars"][:2]
    assert sirius[:3] == pytest.approx(scene_direction(1.7678, math.radians(-16.716)), abs=1e-3)
    assert canopus[:3] == pytest.approx(scene_direction(1.6753, math.radians(-52.696)), abs=1e-3)
    # V magnitudes -1.44 and -0.62 (HYG v4.2): a ratio of 10^(0.4 x 0.82)
    assert sirius[6] / canopus[6] == pytest.approx(10 ** (0.4 * 0.82), rel=1e-3)


@pytest.mark.skipif(not BINARY.exists(), reason="assets/starfield.bin not built")
def test_shipped_binary_size_and_limit():
    data = BINARY.read_bytes()
    info = parse(data)
    assert info["mag_limit"] == pytest.approx(6.5)
    assert 5000 < len(info["stars"]) < 12000
    assert len(data) < 512 * 1024
