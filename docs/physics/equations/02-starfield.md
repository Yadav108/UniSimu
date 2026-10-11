# 02 — Starfield

Used by: Phase 2 (and Phase 4, which lenses the starfield).

## Why
`assets/star_scene.jsx` multiplies each background star by
`0.82 + 0.18·sin(uTime·(0.6 + aPhase·1.7) + aPhase·40)`, which makes them twinkle.
Twinkling (scintillation) comes from turbulence in Earth's atmosphere. An observer in space sees steady points.
The colours are drawn from an invented 5-colour palette.

## 1. Catalogue: HYG v4.2
Source: astronexus.com/projects/hyg (opened).
- The current version is **HYG 4.2 (2025)**.
- **Licence: "Creative Commons Attribution-ShareAlike 4.0"** (quoted from the page).
- Download: `/downloads/catalogs/hygdata_v42.csv.gz`, about 14 MB, also mirrored at codeberg.org/astronexus.

The field names (`ra`, `dec`, `mag`, `ci`, …) are described on the separate "HYG Details" page, which has **not yet been opened**. Confirm them in Phase 2 before writing `tools/build_starfield.py`.

**Licence decision D4 is still open.** A binary derived from CC BY-SA data would probably have to be shared under CC BY-SA, while the repo is MIT.
- Option A: keep the binary in a separate, attributed, CC BY-SA asset folder.
- Option B: use a public-domain source. Hipparcos/Tycho via CDS are candidates; check their terms.

**Ask before committing.**

## 2. Colour index → temperature (Ballesteros 2012)
F. J. Ballesteros, *New insights into black bodies*, EPL 97, 34008 (2012), arXiv:1201.1809 (PDF opened, Eq. 14). **Verified.**

$$T = 4600\left(\frac{1}{0.92(B-V)+1.7}+\frac{1}{0.92(B-V)+0.62}\right)\ \mathrm{K}$$

This is a blackbody approximation, fine-tuned by the author. It is **not** a fit to real stellar atmospheres, so expect errors of a few percent for M stars.

| B−V | T (K) |
|---|---|
| −0.30 | 16 602 |
| 0.00 | 10 125 |
| 0.65 | 5 778 (Sun-like) |
| 1.00 | 4 743 |
| 1.50 | 3 794 |
| 2.00 | 3 169 |

The colour then goes through doc 01 (Planck → XYZ → linear sRGB).

## 3. Magnitude → linear flux
This follows from the Pogson definition in doc 01 §5. For the same band, the relative flux is:

$$\frac{f}{f_{\rm ref}} = 10^{-0.4\,(m - m_{\rm ref})}$$

HYG `mag` is the visual (V) magnitude, so this gives *V-band* relative flux, not bolometric. That is acceptable for a backdrop, but **state it in the phase note**.
Dynamic range check: Sirius (m ≈ −1.46) vs m = 6 gives a ratio of 10^(0.4·7.46) ≈ 960. This needs HDR or a tone map; do not clamp to 8-bit.

## 4. Apparent size (PSF)
A point source has no resolvable disc. The apparent size comes from the camera point-spread function.
- For a circular aperture, the Airy core's first null is at θ ≈ 1.22 λ/D. This standard optics result is **unverified here**; cite a textbook or the Phase 2 note.
- At screen resolution, use a small Gaussian approximating the Airy core, with flux conserved: the sum of the kernel equals the star's flux.
- Diffraction spikes are an artefact of the spider vanes. Make them optional and off by default.

## 5. Coordinates
Convert RA/Dec to a unit vector: (cos δ cos α, cos δ sin α, sin δ), in the equatorial frame.
Choosing a scene "up" axis is a presentation choice; document it.
