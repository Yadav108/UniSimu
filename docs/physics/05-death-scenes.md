# Phase 5: Death scenes

Branch `realism/phase-5-death-scenes`. Equations and sources are in [`equations/05-death-scenes.md`](equations/05-death-scenes.md); §D lists everything opened for this phase.

## Why it was needed
The endings were keyframed animation rather than physics:
- **Supernova:** 7 % of the stage rising to 3 × 10⁹ L☉ at 60 000 K, then `exp(−5x)` decay. Flash, shock and ejecta timings were fractions of the stage, and the whole explosion was treated as a 2000-year phase.
- **Planetary nebula:** a teal and pink tint, also lasting 2000 years.
- **Neutron star:** a fixed-size ball with lighthouse beams always on.

## The physics

### 1. A Type II-P supernova, day by day
A red supergiant's core collapses in under a second. The shock takes **about a day** to reach the surface (Vartanyan et al. 2025), and until then the outside of the star doesn't change. Then:

| Days after collapse | What we show | Source |
|---|---|---|
| 0–1 | The progenitor, unchanged | Vartanyan et al. 2025 (breakout ~1 d) |
| 1–9 | A shock-breakout flash, cooling | **Illustrative** (peak 3 × 10⁴ K, 2 × 10⁹ L☉) |
| 9–143 | The photosphere of the 15 M☉ model s15e12: L and T from Table 4 | Dessart & Hillier 2011 |
| 143–400 | The ⁵⁶Ni → ⁵⁶Co → ⁵⁶Fe decay tail (0.0866 M☉ of ⁵⁶Ni) | Nadyozhin 1994 rates via Yao et al. 2020; lifetimes checked against NNDC |

The **plateau** is the hallmark of a Type II-P. For about 100 days the luminosity stays near 6–8 × 10⁸ L☉. Hydrogen in the ejecta recombines at a fixed temperature (about **5200–5400 K** in the table), and that recombination front sets where the photosphere is. Light keeps coming out at about that temperature while the front eats inward through the expanding ejecta. When it reaches the helium core (~100 d), the light drops by about a dex within a month, onto the radioactive tail: L ∝ e^(−t/111.3 d).

The **radius** follows from Stefan–Boltzmann, as for every other stage: R = √(L/4πσT⁴) ≈ 2 × 10¹⁵ cm on the plateau, matching the table's 2.4–2.5 × 10¹⁵ cm.

### 2. Real durations, so the clock tells the truth
The last timed phase now lasts as long as it really does:
- **Supernova:** 400 days of light curve, about 1.1 yr.
- **Planetary nebula:** 21 000 yr. Its shell expands at 42 km/s and reaches 0.9 pc in that time (Jacob et al. 2013); the code reproduces 0.902 pc.

Each still plays in 10 screen seconds, so Phase 6's clock readout now reads `1 s = 40 d` during a supernova and `1 s = 2.1 kyr` for a planetary nebula.

### 3. A planetary nebula's colour comes from emission lines
A nebula isn't a blackbody: it's thin gas glowing in a few narrow spectral lines. We take NGC 7009's integrated line strengths (Phillips et al. 2010):
- [O III] 500.7 nm: 10.9 × Hβ
- [O III] 495.9 nm: 3.6 ×
- Hα 656.3 nm: 2.79 ×
- [N II] 658.3 nm: 0.126 ×

Each line goes through the same CIE colour-matching functions as the stars (Phase 1). The result is **green-cyan**, which is how [O III]-dominated nebulae look.

The pure-[O III] colour is outside the sRGB gamut: its red component is negative. That negative red outweighs Hα's red, so the red channel clips to zero. A real photograph shows red Hα rims that a single sRGB colour can't carry.

### 4. Neutron stars are tiny, and their beams are radio
The measured radii of a dozen neutron stars are 9.9–11.2 km (Özel & Freire 2016), so the model now uses 10.55 km instead of 11.8 km. Physical mode draws the star at its true scale (the size mapping's minimum). The visible "lighthouse" beam is a radio phenomenon, so in physical mode it only appears under **Illustrative effects**.

## What the existing tests needed (both approved by the owner)
1. **`stage_sequence()`** in `tests/test_stellar.py` sampled the terminal phase using the old shared `TERMINAL_FLASH_YEARS`. It now takes its boundaries from `phase_schedule()`, which gives the same points but the real per-fate lengths. No assertion changed.
2. **`test_supernova_starts_from_the_progenitors_state`** probed at collapse + 0.01 yr (3.65 d), which is now after shock breakout. The probe moved to **half a day**. The 2 % and 5 % assertions are unchanged, because the star really is unchanged then.

I also updated my own Phase 6 test and note: Proxima's clock compression is now 1.6 × 10⁷ (it was 1.7 × 10⁸), because its nebula lasts 21 kyr, not 2 kyr.

**One bug the change exposed:** `evolution_track()` sampled the end of the terminal phase at duration × (1 − 10⁻⁹). For a 1.1-yr supernova at an age of ~10⁷ yr, that's below floating-point resolution, so the H-R track's last "supernova" point landed on the 10⁶ K neutron star and stretched the axis. The margin is now 10⁻⁶ (about 30 s of a 400-day supernova).

## What changed
| File | Change |
|---|---|
| `unisimu/physics/death.py` | **New.** `supernova_state`, `radioactive_luminosity_lsun`, `planetary_nebula_radius_pc`, `emission_line_color`, and the cited tables and constants. |
| `unisimu/physics/stellar.py` | The supernova branch uses `death.supernova_state` (with `stage_progress` = day / 400). `TERMINAL_FLASH_YEARS` is replaced by `SUPERNOVA_YEARS`, `PLANETARY_NEBULA_YEARS` and `terminal_flash_years(mass)`. The old `_supernova_light_curve` and its constants are gone, the neutron-star radius is 10.55 km, and the `evolution_track` margin is fixed. **The signatures of `evolve`, `phase_schedule`, `cinematic_age_years` and `stage_track` are unchanged.** |
| `unisimu/state.py`, `star_scene.py`, `viewport.py`, `controls.py` | **Added** `illustrative_effects` (default off) and its switch, and the optional props `nebula_color` and `illustrative_effects`. |
| `unisimu/copy.py` | The supernova caption no longer claims to outshine the host galaxy. That's true of thermonuclear supernovae, but a Type II-P at ~10⁹ L☉ is roughly a tenth of the Milky Way. |
| `assets/star_scene.jsx` | **Physical mode only:** the supernova body is the photosphere (size and colour from L and T, eased); the planetary nebula uses the line colour; the neutron star is at true scale. Flash, camera shake, shock, ejecta, pulsar beams and remnant shells appear only with **Illustrative effects**. **Stylized mode unchanged** (it still uses `stage_progress`). |
| Tests | `tests/test_death.py` (14 new), plus the two approved edits and my Phase 6 test update. |

## Known simplifications
- **One light curve for every supernova.** All massive presets (8–90 M☉) get the 15 M☉ model's light curve; a real plateau's brightness and length depend on progenitor radius, mass and ⁵⁶Ni (Dessart & Hillier §4).
- **The breakout flash is illustrative.** At 1× playback it lasts only a few ticks (one tick ≈ 2 days of light curve).
- **Colour after the photosphere vanishes.** After 143 d there is no single temperature; the last photospheric T (5550 K) is kept for colour. A real nebular-phase supernova glows in emission lines.
- **Planetary nebula size and brightness are still stylized.** Only its colour and duration are physical. The ~30 kK ionisation onset from the brief wasn't verified, so it isn't used. The line strengths are one nebula's (NGC 7009); others, such as the Ring Nebula, have much stronger [N II].
- **Neutron star.** The 10⁶ K surface temperature is unverified. The remnant shell around a neutron star or black hole is illustrative too: a real supernova remnant forms over centuries, not within this frame.

## How to verify by hand
1. Choose **Look → Physical**, play **Betelgeuse**, and watch the Time panel. During the supernova it should read `1 s = 40 d`, and *In this stage* should count days up to `400 d`.
2. **The supernova:** a brief blue-white brightening, then a long, steady, orange-white glow for about the first quarter of the stage (the plateau), then a fade. There should be no shock shell or particles until you switch on **Illustrative effects**.
3. **The Sun's planetary nebula:** a green-cyan shell, not teal and pink, and *In this stage* reaching `21 kyr`.
4. **Betelgeuse's neutron star:** a tiny point, with no beams unless Illustrative effects is on.
5. Switch to **Stylized**: everything should look exactly as before.

## Tests
`pytest tests/ -q` gives **210 passed** (196 before this phase, plus 14 new):
- unchanged before breakout;
- the light curve passes exactly through all 30 rows of Dessart & Hillier's table;
- the plateau lasts ~100 d and then drops;
- 5000–5600 K across days 50–100, and R = 1–4 × 10¹⁵ cm;
- the tail e-folds with ⁵⁶Co's 111.3 d, and the decay luminosity matches a hand calculation;
- no jump between the plateau and the tail;
- `evolve()` reproduces the light curve in days;
- terminal phases last 400 d and 21 kyr;
- the nebula reaches 0.9 pc;
- the nebula colour is green-cyan, and pure Hα is red;
- the neutron-star radius lies within 9.9–11.2 km.

## Visual check
**Not yet done in a browser.** Use the checklist above; it's tracked in [README.md](README.md).

## References (opened)
- Dessart & Hillier (2011), MNRAS 410, 1739: https://arxiv.org/abs/1008.3238
- Vartanyan et al. (2025), 3D Type II-P supernova: https://arxiv.org/abs/2411.03434
- Yao et al. (2020), quoting the Nadyozhin (1994) decay rates: https://arxiv.org/abs/2005.12922. NNDC NuDat 3 half-lives: https://www.nndc.bnl.gov/nudat3/
- Jacob, Schönberner & Steffen (2013): https://arxiv.org/abs/1307.6189
- Phillips, Cuesta & Ramos-Larios (2010), NGC 7009: https://arxiv.org/abs/1008.4178
- Özel & Freire (2016): https://arxiv.org/abs/1603.02698
