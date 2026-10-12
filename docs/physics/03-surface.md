# Phase 3: The stellar surface

Branch `realism/phase-3-surface`. Equations and sources are in [`equations/03-stellar-surface.md`](equations/03-stellar-surface.md); §7 lists every source opened for this phase.

## Why it was needed
The disc is where a star's physics is most visible to a nearby observer, and the stylized surface invented all of it:
- **Limb darkening:** one linear law with a fixed 0.65 for every star, plus an extra reddening tint toward the edge.
- **Granulation:** a hand-picked noise scale per stage, with the dark lanes tinted by fixed colour multipliers.
- **Starspots:** brightness multiplied by 0.3.
- **Pulsation:** a fixed sine wave of about 3.7 s.
- **Corona:** a bright halo drawn around every star.
- **Bloom:** added light on top of the image, which no camera does.

## The physics, step by step

### 1. Limb darkening: why the edge of a star is dimmer
Looking at the centre of the disc, you see deep into the photosphere, to where it is hotter. Near the edge (the limb) your line of sight grazes the surface and only reaches the cooler upper layers. The standard description is the quadratic law

I(μ)/I(1) = 1 − a(1 − μ) − b(1 − μ)², where μ = cos(angle between the line of sight and the surface normal).

The coefficients come from model atmospheres. We use **Claret & Bloemen (2011)**:
- Johnson **R, V, B** mapped to the red, green and blue channels.
- ATLAS models, solar metallicity, 2 km/s microturbulence.
- Baked by `tools/build_limb_darkening.py` into a 76 × 11 (T_eff × log g) table, and interpolated bilinearly at runtime.

Two effects come straight out of the table:
- **Blue darkens more than red.** For the Sun, a = 0.65 in B but 0.37 in R, so the limb looks slightly redder. The old shader faked this with a tint; now it follows from the data.
- **Cool, low-gravity stars darken much more than hot ones.** A 3500 K supergiant has a(B) ≈ 1.1; a 30 000 K star has a(B) ≈ 0.09.

### 2. Granulation: convection cells sized by the pressure scale height
Hot gas rises, cools at the surface and sinks again, which makes the granulation pattern. A cell's width is set by how quickly pressure falls with height, the **pressure scale height**
H_p = k_B T / (μ m_u g), with surface gravity g = GM/R².

3D simulations give cell diameter ≈ 4 H_p for dwarfs (Magic et al. 2013) and ≈ 15 H_p for red giants (Mathur et al. 2011). We interpolate between the two in log g.

| Star (our model) | log g | H_p | Granules around the circumference |
|---|---|---|---|
| Sun | 4.44 | 135 km | ~8100 (below screen resolution) |
| Sun as a red giant (103 R☉) | 0.41 | 0.79 million km | ~38 |
| Betelgeuse model (705 R☉) | −0.04 | 2.5 million km | ~83 |

**Brightness.** In the solar 3D model, granulation varies the bolometric intensity by 15 % rms. Since I ∝ T⁴, that is ΔT/T ≈ 3.75 %. Each colour channel responds to the temperature change through its own Planck slope, d ln I/d ln T, computed in Python. Blue responds more than red for a cool star, so the dark lanes are automatically redder. Nothing is tinted by hand.

**Hot stars have no granulation.** The surface stops being convective between about 8250 K and 10 000 K (Cantiello & Braithwaite 2019), so the pattern fades out across that range. Sirius (9226 K) sits half-way; Rigel and Eta Carinae on the main sequence show none.

### 3. Starspots: darkness from the Planck law
Sunspot umbrae are 3900–4800 K against the 5772 K photosphere (Solanki 2003). A spot is drawn at the midpoint ratio, about 0.754 T. Its brightness, per channel, is B(T_spot)/B(T): about 22 % in green for the Sun, and darker in blue. This matches Hinode's observation that the darkest umbrae reach about 10 % of the quiet Sun. Spots appear only where there is convection to make them.

### 4. Pulsation: period from the star's density
A star rings like a bell, and the bell's period depends on its mean density. The **pulsation constant** gives
P = Q √(R³/M), with Q = 0.085 d for fundamental-mode red supergiants (Kiss, Szabó & Bedding 2006).

| Star (our model) | Period |
|---|---|
| Betelgeuse model | **392 d** (the real star: ~400 d) |
| The Sun as a red giant | 89 d |

The period now appears in the telemetry for giants. The *animation* runs on a cinematic clock (0.01 s per day, at least 1.5 s per cycle) with a phase accumulator, so the motion stays smooth as the star grows. Only the ratios between stars are physical.

### 5. The corona: a million times fainter
Near the limb, the white-light corona is about **10⁶ times fainter than the disc** (Arregui & Van Doorsselaere 2024). At any exposure that shows the disc, the corona is invisible, so physical mode draws it at exactly that ratio and you don't see it.

The new **Coronagraph** switch does what eclipses and coronagraphs do:
- it blocks the disc (drawn black);
- it raises the corona's exposure by 10⁶.

The corona's streamer pattern is still the stylized one, so treat its shape as illustrative.

### 6. Glare: a camera effect, not the star
Bloom used to *add* light. A real lens spreads part of the light into a halo, but the total stays the same. three.js's UnrealBloomPass adds 9 × strength × (the image's light). That figure comes from its composite shader: `3 · strength · Σ lerpBloomFactor`, and the five factors always sum to 3. So physical mode divides the final exposure by (1 + 9 × strength). With strength 0.05, about 31 % of the light goes into the glow, and the total is unchanged.

The **Camera glare** switch turns it off. The help text says plainly that it is a lens effect.

## What changed
| File | Change |
|---|---|
| `unisimu/physics/surface.py` | **New.** `surface_gravity_cgs`, `pressure_scale_height_m`, `granulation_scale`, `granulation_visibility`, `spot_contrast`, `temperature_sensitivity`, `limb_darkening`, `pulsation_period_days`. |
| `unisimu/physics/limb_darkening_data.py` | **New, generated.** Claret & Bloemen B/V/R quadratic coefficients. |
| `tools/build_limb_darkening.py` | **New offline tool** that generates the file above from VizieR `tableab.dat.gz`. |
| `unisimu/state.py` | **Added** `glare` (default on) and `coronagraph` (default off) with setters. Computed vars: `limb_darkening_coeffs`, `granulation_cells`, `granulation_amplitude`, `convection_visibility`, `temperature_sensitivity_rgb`, `spot_contrast_rgb`, `pulsation_period_days`, `pulsation_display`. Nothing existing changed. |
| `star_scene.py`, `viewport.py` | Nine optional props carry the values above. |
| `controls.py`, `telemetry.py` | Glare and Coronagraph switches in physical mode; a "Pulsation period" row for giants. |
| `assets/star_scene.jsx` | Physical branch of the star shader: per-channel limb darkening, Planck-linearised granulation, Planck spot ratio, and no invented blotches or tints. Physical granule count, faint corona plus coronagraph, energy-conserving glare, and pulsation from the period. **Stylized mode unchanged.** |
| `tests/test_surface.py` | 13 new tests (below). |

## Known simplifications
- **Supergiant granules are too small.** The Betelgeuse model has about 83 cells; interferometry shows only a handful. Those huge cells are set by the deep envelope, not H_p, and no supergiant-specific factor was found.
- **Masses and metallicity are simplified.** Surface terms use the **initial** mass, since mass loss isn't modelled. Limb darkening is for solar metallicity, and it is clamped to the table (3500–50 000 K, log g 0–5): Proxima (3050 K) uses the 3500 K values, and a white dwarf the log g 5 values.
- **The noise pattern is still procedural.** Granulation and spot *patterns* come from noise. Only their size, contrast and colour are physical. The ±1 noise range is assumed to match the 15 % rms contrast; the true rms of the GLSL noise was not measured.
- **Spots are scaled from the Sun.** Every star's spots are assumed to have the solar umbra/photosphere temperature ratio.
- **Granulation fades below screen resolution.** When more than 160 granules would fit around the limb, the pattern fades out, much as the real Sun's granulation can't be seen on a full-disc image. So the main-sequence Sun looks smooth, as it really does at that scale.
- **The coronagraph only boosts the corona.** A real coronagraph exposure would also boost the starfield.

## How to verify by hand
1. Choose **Look → Physical** with Exposure **Auto**.
2. Play **Betelgeuse** to the red-supergiant stage. You should see:
   - a few dozen large granules, with redder lanes;
   - a strong dark limb that is redder at the edge;
   - a slow swell, with the telemetry showing a pulsation period of a few hundred days.
3. **The Sun on the main sequence** should be a smooth disc with gentle limb darkening and no visible granules (they are below resolution).
4. **Rigel on the main sequence** should have no granulation or spots, and a much flatter limb.
5. Turn on **Coronagraph**: the disc goes black and the corona appears. Turn it off and the corona vanishes. That is the 10⁶ ratio.
6. Toggle **Camera glare**. The halo appears and disappears, while the star's overall brightness stays the same.
7. Switch to **Stylized**: it should look exactly as before.

## Tests
`pytest tests/ -q` gives **177 passed** (164 before this phase, plus 13 new):
- solar log g = 4.44 and H_p within 100–150 km;
- Betelgeuse's granules are more than 10⁴ times the Sun's, with over 50 times fewer around the circumference;
- no granulation above 10 000 K;
- the interpolated table reproduces the Claret & Bloemen grid point exactly;
- blue limb-darkens more than red at four temperatures, and darkening weakens monotonically from 4000 to 40 000 K;
- the limb profile stays within [0, 1] across the **entire** grid, and clamps outside it;
- spot contrast equals the Planck ratio, darkest in blue;
- temperature sensitivity follows the Wien and Rayleigh–Jeans limits;
- Betelgeuse's period is 392 d, and P scales with √(R³/M).

## Visual check
**Not yet done in a browser**, for the same memory and extension constraints as Phases 1 and 2. Use the checklist above; it is tracked in [README.md](README.md).

## New dependencies
None.

## References (opened)
- Claret & Bloemen (2011), A&A 529, A75. VizieR: https://cdsarc.cds.unistra.fr/ftp/J/A+A/529/A75/
- Magic et al. (2013), Stagger grid I: https://arxiv.org/abs/1302.2621
- Mathur et al. (2011), granulation in red giants: https://arxiv.org/abs/1109.1194
- Cantiello & Braithwaite (2019), envelope convection in A/B stars: https://arxiv.org/abs/1904.02161
- Murphy et al. (2026), KRONOS II (quoting Solanki 2003): https://arxiv.org/abs/2606.16782
- Tiwari et al. (2015), Hinode sunspot properties: https://arxiv.org/abs/1508.04830
- Kiss, Szabó & Bedding (2006), red supergiant pulsation: https://arxiv.org/abs/astro-ph/0608438
- Arregui & Van Doorsselaere (2024), coronal heating chapter: https://arxiv.org/abs/2409.13318
- IAU 2015 Resolution B3: https://arxiv.org/abs/1510.07674. NIST CODATA 2022 (G, m_u, k_B): https://physics.nist.gov/cuu/Constants/
- three.js r185 `UnrealBloomPass.js` (composite shader), read from `.web/node_modules`.
