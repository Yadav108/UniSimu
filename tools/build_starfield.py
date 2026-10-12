"""Bake the HYG star catalogue into the compact starfield binary the scene loads.

Offline tool, not imported by the app. Usage (from the repo root):

    python tools/build_starfield.py path/to/hygdata_v42.csv.gz [--out assets/starfield.bin]

Input: HYG database v4.2 (astronexus.com/projects/hyg), CC BY-SA 4.0.
The output is a derived work and is distributed under the same licence; see
assets/starfield.LICENSE.md. Equations: docs/physics/equations/02-starfield.md.

Binary layout (little-endian):
    header   b"USF1", uint32 star_count, float32 mag_limit, uint16 glow_w, uint16 glow_h
    stars    star_count x 7 float32: scene direction X, Y, Z (unit vector);
             linear sRGB colour r, g, b (luminance 1); V-band flux relative to mag 0.
             Sorted brightest first, so a prefix is a brighter-only subset.
    glow     glow_h x glow_w x 3 float32: diffuse sky brightness from the fainter
             stars (mag_limit < V <= glow_limit), in mag-0 flux per steradian, per
             linear sRGB channel. Equirectangular: column = RA (0 .. 2 pi), row 0 =
             Dec +90. Only an approximation of the Milky Way's glow.
"""

import argparse
import csv
import gzip
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unisimu.physics.blackbody import REFERENCE_TEMPERATURE_K, blackbody_display_color  # noqa: E402
from unisimu.physics.starfield import bv_to_temperature, relative_flux, scene_direction  # noqa: E402

MAGIC = b"USF1"
HEADER = struct.Struct("<4sIfHH")
STAR = struct.Struct("<7f")
DEFAULT_MAG_LIMIT = 6.5
DEFAULT_GLOW_LIMIT = 9.0
GLOW_W, GLOW_H = 128, 64
GLOW_SMOOTH_ROWS = 2  # +-2 rows (~11 deg in Dec)
GLOW_SMOOTH_COLS = 2  # +-2 columns at the equator, wider toward the poles
# Ballesteros' formula has a pole at B-V = -0.674; real stars sit well inside this range.
BV_RANGE = (-0.4, 2.0)


def star_colour(ci: str) -> tuple[float, float, float]:
    """Unit-luminance linear sRGB from a B-V string; neutral (5772 K) when missing."""
    if ci.strip() == "":
        temperature = REFERENCE_TEMPERATURE_K
    else:
        bv = min(max(float(ci), BV_RANGE[0]), BV_RANGE[1])
        temperature = bv_to_temperature(bv)
    return blackbody_display_color(temperature)[0]


def read_catalogue(path: Path):
    """Yield (ra_rad, dec_rad, mag, ci) for every star except the Sun (id 0)."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] == "0" or row["mag"] == "":
                continue
            yield float(row["rarad"]), float(row["decrad"]), float(row["mag"]), row["ci"]


def build(rows, mag_limit: float = DEFAULT_MAG_LIMIT, glow_limit: float = DEFAULT_GLOW_LIMIT) -> bytes:
    stars = []
    glow = [[0.0, 0.0, 0.0] for _ in range(GLOW_W * GLOW_H)]
    for ra, dec, mag, ci in rows:
        if mag <= mag_limit:
            stars.append((relative_flux(mag), scene_direction(ra, dec), star_colour(ci)))
        elif mag <= glow_limit:
            col = min(int((ra % (2 * math.pi)) / (2 * math.pi) * GLOW_W), GLOW_W - 1)
            row = min(int((math.pi / 2 - dec) / math.pi * GLOW_H), GLOW_H - 1)
            flux = relative_flux(mag)
            cell = glow[row * GLOW_W + col]
            for i, c in enumerate(star_colour(ci)):
                cell[i] += flux * c
    stars.sort(key=lambda s: -s[0])

    out = bytearray(HEADER.pack(MAGIC, len(stars), mag_limit, GLOW_W, GLOW_H))
    for flux, direction, colour in stars:
        out += STAR.pack(*direction, *colour, flux)
    # Spread each cell's flux evenly over a patch of neighbouring cells, then
    # divide by solid angle. Scattering *flux* conserves the total exactly.
    # The patch is GLOW_SMOOTH_ROWS rows tall and, because cells shrink toward
    # the poles (solid angle ~ cos Dec), ~1/cos(Dec) times wider there, so a
    # lone faint star never becomes a spike or a streak.
    d_ra = 2 * math.pi / GLOW_W
    solid_angles = []
    for row in range(GLOW_H):
        dec_top = math.pi / 2 - row * math.pi / GLOW_H
        solid_angles.append(d_ra * (math.sin(dec_top) - math.sin(dec_top - math.pi / GLOW_H)))
    smoothed = [[0.0, 0.0, 0.0] for _ in range(GLOW_W * GLOW_H)]
    for row in range(GLOW_H):
        cos_dec = math.cos(math.pi / 2 - (row + 0.5) * math.pi / GLOW_H)
        half_cols = min(GLOW_W // 2, max(GLOW_SMOOTH_COLS, round(GLOW_SMOOTH_COLS / max(cos_dec, 1e-3))))
        rows = range(max(row - GLOW_SMOOTH_ROWS, 0), min(row + GLOW_SMOOTH_ROWS, GLOW_H - 1) + 1)
        share = 1.0 / (len(rows) * (2 * half_cols + 1))
        for col in range(GLOW_W):
            flux = glow[row * GLOW_W + col]
            if not any(flux):
                continue
            for r in rows:
                for k in range(-half_cols, half_cols + 1):
                    target = smoothed[r * GLOW_W + (col + k) % GLOW_W]
                    for i in range(3):
                        target[i] += flux[i] * share
    for row in range(GLOW_H):
        for col in range(GLOW_W):
            out += struct.pack("<3f", *(v / solid_angles[row] for v in smoothed[row * GLOW_W + col]))
    return bytes(out)


def parse(data: bytes) -> dict:
    """Inverse of build(), for tests and inspection."""
    magic, count, mag_limit, glow_w, glow_h = HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError("not a UniSimu starfield file")
    offset = HEADER.size
    stars = [STAR.unpack_from(data, offset + i * STAR.size) for i in range(count)]
    offset += count * STAR.size
    glow = struct.unpack_from(f"<{glow_w * glow_h * 3}f", data, offset)
    return {"mag_limit": mag_limit, "stars": stars, "glow_w": glow_w, "glow_h": glow_h, "glow": glow}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path, help="hygdata_v42.csv or .csv.gz")
    parser.add_argument("--out", type=Path, default=Path("assets/starfield.bin"))
    parser.add_argument("--mag-limit", type=float, default=DEFAULT_MAG_LIMIT)
    parser.add_argument("--glow-limit", type=float, default=DEFAULT_GLOW_LIMIT)
    args = parser.parse_args()
    data = build(read_catalogue(args.catalogue), args.mag_limit, args.glow_limit)
    args.out.write_bytes(data)
    info = parse(data)
    print(f"wrote {args.out}: {len(info['stars'])} stars (V <= {args.mag_limit}), "
          f"{info['glow_w']}x{info['glow_h']} glow map, {len(data) / 1024:.0f} KiB")


if __name__ == "__main__":
    main()
