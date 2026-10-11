# 03 — Stellar surface: limb darkening, granulation, spots, pulsation

Used by: Phase 3.

## Why
Today's surface uses values that don't depend on the star:
- **Limb darkening:** a *linear* law, `limb = 1 − 0.65(1−μ)`, plus an extra invented reddening toward the limb.
- **Granulation:** one noise scale per stage (`SURFACE_BY_STAGE.cell`).
- **Spots:** a brightness multiplier.
- **Pulsation:** a fixed ~3.7 s wall-clock sine.

All four should depend on T, g and R.

## 1. Limb darkening laws
Reeve & Howarth, *Limb-darkening coefficients from line-blanketed non-LTE hot-star model atmospheres*, MNRAS (2016), arXiv:1511.02029 (PDF opened, Eqs. 1–3). **Verified.**

- Linear: I(μ) = I(1)[1 − u(1−μ)] (their Eq. 1)
- Quadratic: I(μ) = I(1)[1 − u₁(1−μ) − u₂(1−μ)²] (their Eq. 2)
- Claret 4-parameter: I(μ) = I(1)[1 − Σ_{k=1..4} a_k(1 − μ^{k/2})] (their Eq. 3)

Here μ = cos θ, the angle between the line of sight and the surface normal.

**Discrepancy with the brief:** arXiv:1511.02029 is *Reeve & Howarth* and covers only **hot stars (15–55 kK)**.
It cannot supply coefficients for the Sun, red giants or red dwarfs.

For cool stars the candidate is **Claret & Bloemen (2011), A&A 529, A75**, VizieR catalogue `J/A+A/529/A75`
(https://cdsarc.cds.unistra.fr/viz-bin/cat/J/A+A/529/A75 resolves). The landing page has placeholders instead of
its title, authors and coverage, so **its T_eff/log g range, passbands and laws are unverified** until the ReadMe is opened in Phase 3.

Plan for Phase 3: an offline script pulls the B, V and R (or Sloan g, r, i) quadratic coefficients on a coarse T_eff × log g grid from both catalogues. The script and its data stay outside the app. A small table baked into `unisimu/physics/surface.py` is interpolated per colour channel. Above 55 kK, hold the edge value.

The expected trend (to test against the table, not assumed): at fixed T, bluer bands darken more strongly than red bands.

## 2. Surface gravity and pressure scale height

$$g = \frac{GM}{R^2},\qquad H_p = \frac{k_B T}{\mu\, m_{\rm H}\, g}$$

- μ is the mean molecular weight: about 1.3 for neutral solar-mix photospheres. This is an **assumption; document it**.
- m_H = 1.6735 × 10⁻²⁷ kg.
- G = 6.674 30 × 10⁻¹¹ m³ kg⁻¹ s⁻². This is the CODATA value, **not opened in this session** (**unverified**; check in Phase 3).

## 3. Granule size ∝ H_p
Magic et al., *The Stagger-grid… I*, A&A (2013), arXiv:1302.2621 (PDF opened). **Verified:**
- The abstract says: "The granule size correlates closely with the pressure scale height sampled at the depth of maximum velocity."
- §3.1.5 gives the Nordlund scaling relation d_NSR = 4 (v_h/v_z) H_P ≈ 4 H_P. The residuals are about 30 %.
- Their grid covers 4000–7000 K and log g 1.5–5.0.

Mathur et al., *Granulation in red giants…*, ApJ (2011), arXiv:1109.1194 (PDF opened). **Verified:**
- They use d ∝ H_p ∝ T_eff/g.
- They say that simulations give red-giant granules "≈ 15 H_p wide". That shows the proportionality constant is **not** universal.

**Model to implement (`granulation_scale(T, M, R)`):**
- Cell diameter d ≈ k·H_p, with k = 4 by default.
- The shader gets the number of cells around the circumference, N ≈ 2πR/d.
- Clamp N to a renderable range, e.g. 3 to 400.
- Stars hotter than about 7–8 kK have **no surface convection zone**. That threshold is the commonly cited end of the convective envelope, and is **unverified here**. Fade granulation out above it.

Sanity values (computed with μ = 1.3; the Betelgeuse inputs 3600 K, 16.5 M☉, 764 R☉ are *illustrative, not cited*):

| Star | H_p | H_p / R | N ≈ 2πR/(4H_p) |
|---|---|---|---|
| Sun (5772 K, 1 M☉, 1 R☉) | ≈ 134 km | 1.9 × 10⁻⁴ | ≈ 8000, clamped |
| Betelgeuse | ≈ 4.2 R☉ | 5.5 × 10⁻³ | ≈ 280 by this formula |

**Note:** with k = 4 the formula still gives hundreds of cells for Betelgeuse. Interferometry shows only a few giant cells, and Mathur's "15 H_p" plus the deeper sampling depth push d up a lot. In Phase 3, take k for giants from a cited 3D supergiant result, e.g. Chiavassa et al. (Betelgeuse RHD models, **not opened**), instead of tuning it by eye.

The test the prompt requires holds by construction: H_p/R is about 30× larger for Betelgeuse, and the absolute cell size is about 2 × 10⁴× larger.

## 4. Spot contrast from Planck
The intensity ratio of a spot at T_s to the photosphere at T, at wavelength λ:

$$C(\lambda)=\frac{B_\lambda(\lambda,T_s)}{B_\lambda(\lambda,T)}$$

Per channel, use the ratio of the doc 01 linear RGB values at T_s and at T.
The brief says umbrae are 1000–2000 K cooler on Sun-like stars. This is **unverified**; cite a sunspot review in Phase 3.

## 5. Pulsation timescale
Dynamical (free-fall) time:

$$t_{\rm dyn}=\sqrt{\frac{R^3}{GM}}$$

- Sun ≈ 27 min. Betelgeuse (illustrative inputs above) ≈ 96 d.
- The real fundamental period is Q/√(ρ̄/ρ̄☉), with a pulsation constant Q of a few hundredths of a day. That relation is **unverified here**; cite it in Phase 3.
- Observed Betelgeuse periods (~400 d) are of order several t_dyn.
- Either way, the visual period is **cinematic**: map it through the time-honesty rules in doc 06.

## 6. Corona and bloom (no equation, a constraint)
The claim that the corona is about 10⁻⁶ of the disc's brightness comes from the brief and is **unverified** (find a solar-eclipse photometry reference).

Physical mode draws no halo except the camera PSF. The bloom becomes one energy-conserving kernel: the kernel sums to 1, so total flux is unchanged. Label it as a camera artefact.
