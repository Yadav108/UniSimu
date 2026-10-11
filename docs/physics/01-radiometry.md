# Phase 1: Radiometry and colour

Branch `realism/phase-1-radiometry`. Equations and sources are in [`equations/01-radiometry-color.md`](equations/01-radiometry-color.md).

## Why it was needed
Before this phase, a star's colour came from the Tanner Helland curve fit. That fit returns 8-bit sRGB, clamps at 1000–40 000 K, and carries no brightness. Brightness was a hand-picked constant per stage, so:
- a 3050 K red dwarf and the Sun were drawn about equally bright;
- every star hotter than 40 000 K had the same colour;
- HDR values above 1 were simply clipped, because no tone mapping was set.

Every later phase works in light: limb darkening, spot contrast, Doppler beaming and supernova cooling. So the light itself has to be right first.

## The physics, in one line each
1. **Planck's law** gives the spectrum a surface at temperature T emits:
   B_λ(λ, T) = 2hc² / λ⁵ · 1 / (e^{hc/λk_BT} − 1).
2. **The eye or camera response** is the three CIE 1931 colour-matching functions x̄, ȳ, z̄, using the Wyman–Sloan–Shirley analytic fit.
   Multiply the spectrum by each one and add over 360–830 nm to get the tristimulus values X, Y, Z. **Y is luminance**: how bright the surface looks.
3. **To screen primaries:** a 3×3 matrix turns XYZ into *linear* sRGB.
   The code builds that matrix from the published sRGB primaries and the D65 white point, instead of hard-coding 9 numbers, and a test checks that D65 maps to (1, 1, 1).
4. **One tone map at the very end** squeezes the HDR values into the display's range. It is Khronos PBR Neutral, which three.js calls `NeutralToneMapping`. It was chosen because it bends hues less than ACES, and hue *is* the information here.

**Why "linear"?** Light adds linearly: two lamps give twice the photons. sRGB hex codes are gamma-encoded for the display.
Doing arithmetic on gamma-encoded numbers (dimming a spot, adding bloom) gives the wrong result, so everything stays linear until the final `OutputPass`.

## What changed
| File | Change |
|---|---|
| `unisimu/physics/blackbody.py` | **Added** `planck_spectral_radiance`, `cie1931_cmf`, `blackbody_xyz`, `chromaticity`, `xyz_to_linear_srgb`, `blackbody_linear_rgb`, `blackbody_display_color` (cached), and the matrices `LINEAR_SRGB_TO_XYZ` / `XYZ_TO_LINEAR_SRGB`. `kelvin_to_rgb` and `kelvin_to_hex` are unchanged and still used by stylized mode. |
| `unisimu/state.py` | **Added** `render_mode` (default `"stylized"`) and `exposure_mode` (default `"auto"`) with their setters, plus the computed vars `surface_color_linear` and `surface_luminance`. Nothing existing was renamed. |
| `unisimu/components/star_scene.py`, `viewport.py` | **Added** optional props `surface_color`, `surface_luminance`, `render_mode`, `exposure_mode`. In JS they arrive as `surfaceColor` etc. |
| `unisimu/components/controls.py` | **Added** a "Look" toggle (Stylized / Physical), and an "Exposure" toggle (Auto / Fixed) with one line of help text. |
| `assets/star_scene.jsx` | Physical mode does three things: the star body uses the linear surface colour; its brightness is `surface_luminance × exposure`; and the renderer switches to Neutral tone mapping. Stylized mode runs exactly as before. Also added an **optional test mode**: `?unisimuSeed=N&unisimuFreeze=T` seeds every random choice (`mulberry32`) and pins the animation clock. It does nothing without those URL parameters. |
| `tests/test_radiometry.py` | 20 new tests (below). |
| `tests/visual/capture_baseline.py` | `--render-mode`, `--exposure` and `--seed` options. |
| Corona (interim) | In physical mode the stylized corona dims with the body exposure (capped at 1), so a dim star no longer wears a bright halo. Phase 3 replaces it. |
| `requirements-dev.txt` | New: `playwright` (dev only). |

## Exposure: what the two settings mean
`surface_luminance` is the surface brightness relative to a 5772 K surface. This is **per unit area**: a resolved disc looks equally bright at any distance, and only its apparent size changes.

| Star (surface T) | Relative surface luminance |
|---|---|
| Proxima, 3050 K | 0.019 |
| Sun, 5772 K | 1 |
| Sirius A, 9226 K | 5.7 |
| White dwarf, 25 000 K | 49.6 |
| Eta Carinae MS, 47 000 K | ≈ 123 |
| PN core, 100 000 K | ≈ 308 |

- **Auto** sets every star's surface to the same level (1.0). Only the colour differs. This is the "compare colours" view.
- **Fixed** uses one exposure for every star (a 5772 K surface lands at 1.0). A red dwarf is a dull ember and a hot supergiant saturates to white. This is what one camera setting would record (decision D1, camera-like).

**Why visible luminance and not T⁴?** σT⁴ is the *total* energy across all wavelengths. A camera only sees 360–830 nm. A hot star pours most of its energy into the ultraviolet, so its visible brightness grows much more slowly than T⁴, while a cool star loses most of its light into the infrared.

The tests check both: the Planck integral reproduces σT⁴ to 0.1 %, and the visible Y grows strictly with T.

## Known simplifications (handled in later phases)
- Only the **star body** is physical so far. These are still stylized in physical mode:
  - the corona halo, bloom and limb reddening (Phase 3);
  - the starfield (Phase 2);
  - the nebula, supernova and black-hole effects (Phases 4–5).
- The supernova keeps its keyframed size animation. Its brightness now follows the snapshot temperature.
- **White balance (D3):** absolute colorimetry only, with D65 white. The optional "adapt to this star" toggle is not built yet.
- Colours below about 1900 K fall outside the sRGB gamut (negative blue). They are clipped *after* the luminance is computed, so brightness is preserved.
- `stellar.py` still uses T☉ = 5778 K. The new code uses the IAU nominal 5772 K only as its brightness reference. The 0.1 % mismatch is harmless, and changing `stellar.py` would touch existing tests.

## How to verify by hand
- `python -c "from unisimu.physics.blackbody import chromaticity; print(chromaticity(5772))"` gives about (0.3263, 0.3361), just warm of D65 (0.3127, 0.3290).
- In the app, choose **Look → Physical**, then **Exposure → Fixed**, and step through the presets:
  - Proxima should be a dim orange ember;
  - the Sun should be near white;
  - Sirius should be bright blue-white;
  - Eta Carinae's main sequence should be blown out.
- Switch back to **Stylized**: it should look exactly as before.

## Tests
`pytest tests/ -q` gives **148 passed**: the 128 existing tests, unchanged, plus 20 new ones in `tests/test_radiometry.py`:
- chromaticity at 1667, 3000, 5772, 10 000 and 30 000 K matches the reference table to 0.001;
- the Planckian locus moves monotonically toward blue;
- D65 maps to RGB (1, 1, 1), and the luminance row is (0.2126, 0.7152, 0.0722);
- ȳ peaks at 550–560 nm;
- 5772 K is near white, 3000 K is orange and not red, 30 000 K is blue-white;
- luminance increases strictly with T, and the display colour has luminance 1 with no negative channels (with the out-of-gamut 1200 K case checked);
- T = 0 emits nothing, and extreme temperatures don't raise;
- ∫B dλ reproduces σT⁴ to 0.1 %, and 8000 K vs 4000 K gives a ratio of 16;
- the snapshot's L, R and T satisfy Stefan–Boltzmann;
- the reference temperature is 5772 K.

## Screenshots
Captured with `tests/visual/capture_baseline.py --render-mode physical --exposure fixed --seed 1` (headless Chromium using SwiftShader). The frames are kept local, not committed.

**Only part of the set was captured.** Physical/fixed finished for **Proxima and the Sun** (all 5 stages each). The remaining presets, physical/auto and a seeded stylized set were not captured:
- Physical mode under SwiftShader runs at about 12 min per preset;
- then Claude Code stopped both the dev server and the capture because the machine ran critically low on memory.

They still need to run in a real browser or on a machine with more headroom.

What the captured frames show:
- **Fixed exposure behaves as intended.**
  - Proxima's main sequence (3050 K) is a dull ember.
  - The Sun's main sequence looks nearly as it does in stylized mode (luminance 1), just slightly softer under the Neutral tone map.
  - Red giants are darker orange-brown, because cooler means dimmer.
  - The planetary-nebula and white-dwarf cores (25 000–100 000 K) blow out to a white glare.
- **The first physical capture, before the interim corona fix,** showed the stylized corona at full strength around a near-black Proxima. It looked like a solar eclipse. That is why the corona is now tied to the body's exposure.
- **Still to check:** physical/auto for all presets, and that stylized mode looks unchanged. Stylized code paths only gained `rand()` (identical to `Math.random` without the URL flag) and a `motion` factor that is 1 unless the scene is frozen.

## References (all opened during the research step)
- Wyman, Sloan & Shirley (2013), JCGT 2(2): https://jcgt.org/published/0002/02/01/
- NIST CODATA 2022 (h, c, k_B, σ): https://physics.nist.gov/cuu/Constants/
- ICC sRGB registry (primaries, D65, transfer curve): https://registry.color.org/rgb-registry/srgb
- IAU 2015 Resolution B3, T_eff,☉ = 5772 K: https://arxiv.org/abs/1510.07674
- IAU 2015 Resolution B2 (magnitudes, for later exposure work): https://arxiv.org/abs/1510.06262
- Khronos PBR Neutral tone mapper: as shipped in three.js r185 `NeutralToneMapping`. I did not open the specification document itself (**unverified**).
