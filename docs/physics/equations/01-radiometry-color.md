# 01 — Radiometry and colour

Used by: Phase 1 (and indirectly every later phase that turns a temperature into a colour).

## Why
`unisimu/physics/blackbody.py` currently uses the Tanner Helland piecewise fit to Mitchell Charity's
blackbody table. It returns 8-bit sRGB, clamps at 1000–40 000 K, and carries no brightness.
Above 40 kK every star gets the same colour, so the 60 kK supernova peak, the 100 kK planetary-nebula
core and the 10⁶ K neutron star all look alike. A physical pipeline goes
**spectrum → CIE XYZ → linear sRGB (HDR) → one tone map at the end**.

## 1. Planck's law (spectral radiance)

$$B_\lambda(\lambda,T) = \frac{2hc^2}{\lambda^5}\,\frac{1}{e^{hc/(\lambda k_B T)}-1}\qquad[\mathrm{W\,sr^{-1}\,m^{-3}}]$$

| Symbol | Meaning | Value (SI, exact since the 2019 redefinition) |
|---|---|---|
| h | Planck constant | 6.626 070 15 × 10⁻³⁴ J s |
| c | speed of light | 299 792 458 m s⁻¹ |
| k_B | Boltzmann constant | 1.380 649 × 10⁻²³ J K⁻¹ |
| λ | wavelength | m (the CIE fit below takes nm) |
| T | temperature | K |

- Source: NIST CODATA 2022, h — https://physics.nist.gov/cgi-bin/cuu/Value?h (opened; listed as exact). **Verified.**
- Implementation note: use `math.expm1` for the denominator so that large λT stays accurate.

## 2. CIE 1931 colour-matching functions: multi-lobe analytic fit

Wyman, Sloan & Shirley, *Simple Analytic Approximations to the CIE XYZ Color Matching Functions*,
JCGT 2(2), 2013 — https://jcgt.org/published/0002/02/01/ (PDF opened; Eq. 4, Table 1 and Listing 1 checked). **Verified.**

Piecewise Gaussian with a different width on each side of the peak:

$$g(\lambda;\mu,\sigma_1,\sigma_2)=\exp\!\Big(-\tfrac12\big[(\lambda-\mu)\,S(\lambda-\mu,\sigma_1,\sigma_2)\big]^2\Big),\quad S(x,a,b)=\begin{cases}a & x<0\\ b & x\ge 0\end{cases}$$

Note that the paper's σ values are *inverse* widths (nm⁻¹); they multiply (λ−μ).

```
x̄(λ) = 0.362 g(λ; 442.0, 0.0624, 0.0374) + 1.056 g(λ; 599.8, 0.0264, 0.0323) − 0.065 g(λ; 501.1, 0.0490, 0.0382)
ȳ(λ) = 0.821 g(λ; 568.8, 0.0213, 0.0247) + 0.286 g(λ; 530.9, 0.0613, 0.0322)
z̄(λ) = 1.217 g(λ; 437.0, 0.0845, 0.0278) + 0.681 g(λ; 459.0, 0.0385, 0.0725)
```
λ is in nm. The paper reports that this fit's error is smaller than the variance between the human-subject measurements behind the CIE standard.

Tristimulus values:

$$X=\int B_\lambda(\lambda,T)\,\bar x(\lambda)\,d\lambda,\ \text{etc.}\quad(360\text{–}830\text{ nm},\ 1\text{ nm steps is plenty})$$

Chromaticity is x = X/(X+Y+Z), y = Y/(X+Y+Z).

## 3. XYZ → linear sRGB (D65)

sRGB primaries and white point, from the ICC registry — https://registry.color.org/rgb-registry/srgb (opened). **Verified.**

| | x | y |
|---|---|---|
| R | 0.64 | 0.33 |
| G | 0.30 | 0.60 |
| B | 0.15 | 0.06 |
| White D65 | 0.3127 | 0.3290 |

The registry page does not print the matrix. We derive it from the primaries and white point with the standard
construction: put each primary's XYZ (at Y = 1) in a column, then scale the columns so that RGB = (1,1,1) maps to D65.
This derivation is **computed here (scratch script)** and should be re-derived in code rather than hard-coded:

```
XYZ→linear sRGB
[ 3.240970 -1.537383 -0.498611]
[-0.969244  1.875968  0.041555]
[ 0.055630 -0.203977  1.056972]
```
The forward matrix's middle row (0.212639, 0.715169, 0.072192) gives the luminance weights.

Encoding transfer function, used only at the very end in the `OutputPass`. Source: same registry page. **Verified.**
`C' = 12.92·C` for C ≤ 0.0031308, otherwise `C' = 1.055·C^(1/2.4) − 0.055`.

Out-of-gamut values: a blackbody below ~1900 K gives slightly negative linear blue
(see the table). Clip negatives to 0 **after** computing luminance, and document this.

## 4. Stefan–Boltzmann and solar units

$$L = 4\pi R^2\sigma T^4\quad\Longrightarrow\quad \frac{L}{L_\odot}=\Big(\frac{R}{R_\odot}\Big)^2\Big(\frac{T}{T_\odot}\Big)^4$$

- σ = 5.670 374 419… × 10⁻⁸ W m⁻² K⁻⁴ (exact). NIST CODATA 2022 — https://physics.nist.gov/cgi-bin/cuu/Value?sigma (opened). **Verified.**
- Nominal solar values (IAU 2015 Resolution B3): L☉ = 3.828 × 10²⁶ W. The **3.828 × 10²⁶ W** value is quoted inside Resolution B2 (below), so it is **verified**.
  - T☉ = 5772 K and R☉ = 6.957 × 10⁸ m are B3 values I have **not yet opened** (**unverified**). The Phase 1 note must open IAU 2015 B3 (arXiv:1510.07674) before these go into code.
- **Discrepancy with the code:** `stellar.py` uses T☉ = 5778 K. Switching to 5772 K would change existing outputs by about 0.1 %. **Do not change it without asking.** Existing tests are read-only (constraint 8).

## 5. Flux and magnitudes (exposure)

Irradiance at distance d:

$$f = \frac{L}{4\pi d^2}$$

Bolometric magnitudes, from IAU 2015 Resolution B2 — arXiv:1510.06262 (opened, Eqs. 1–4). **Verified.**
- Absolute: M_Bol = −2.5 log₁₀(L / L₀), with L₀ = 3.0128 × 10²⁸ W. This gives M_Bol,☉ ≈ 4.74.
- Apparent: m_Bol = −2.5 log₁₀(f / f₀), with f₀ = 2.518 021 002 × 10⁻⁸ W m⁻².

**Exposure use:** "fixed physical exposure" scales radiance by a constant chosen once (e.g. so that the Sun at 1 AU just saturates).
"Auto exposure" picks a scale per star. Either way, the **ratio** between two stars viewed at the same distance must equal the ratio of their radiances (∝ T⁴ for surface brightness).

## Sanity values (computed with the formulas above; use them as test oracles)

| T (K) | chromaticity (x, y) | linear sRGB, normalised to max channel | Expect |
|---|---|---|---|
| 1667 | (0.5613, 0.4065) | (1.000, 0.187, −0.015) | deep orange, slightly out of gamut |
| 3000 | (0.4358, 0.4052) | (1.000, 0.485, 0.155) | **orange, not red** |
| 3200 | (0.4223, 0.3999) | (1.000, 0.523, 0.195) | the repo's red-giant tip |
| 5772 | (0.3263, 0.3361) | (1.000, 0.881, 0.822) | **near white**, slightly warm |
| 10 000 | (0.2807, 0.2884) | (0.610, 0.696, 1.000) | blue-white |
| 30 000 | (0.2502, 0.2488) | (0.362, 0.498, 1.000) | **blue-white** |
| 100 000 | (0.2427, 0.2381) | (0.315, 0.453, 1.000) | converges toward the blue limit |

Planckian-locus cross-check: the computed chromaticities agree with the Kim et al. (2002) cubic-spline approximation of the locus
to within 0.004 in x and y over 1667–25 000 K. The Kim et al. coefficients were typed from memory: **unverified**.
Use them only as a secondary check; the primary oracle is the integral itself.

**Tests to write (Phase 1):**
- The chromaticity values in the table to 1e-3.
- Y(T) strictly increasing.
- Bolometric ∫B dλ ∝ T⁴, so the ratio for 2T vs T is 16 within the integration error.
- `luminosity_from_radius_temperature` is consistent with Stefan–Boltzmann.
