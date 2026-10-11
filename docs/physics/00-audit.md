# Phase 0: Read-only audit

Branch `realism/phase-0-audit`. This phase changes no application code. The only additions are this note, the capture script
`tests/visual/capture_baseline.py` and its output. The equations and sources live in [`equations/`](equations/README.md).

## Why this phase exists
Before changing how anything looks, we need three things:
1. a map of what the code does now;
2. a record of every number in the renderer that was chosen by eye;
3. a baseline (tests and screenshots) to measure regressions against.

You can't tell whether a change broke something without a record of what it looked like before.

---

## 1. File-by-file map

| File | Role |
|---|---|
| `unisimu/physics/stellar.py` | The whole stellar model: `evolve(mass, age) -> StellarSnapshot`, `stage_track`, `phase_schedule`, `cinematic_age_years`, `evolution_track`. Standard library only, uncited "simplified scaling relations". |
| `unisimu/physics/blackbody.py` | `kelvin_to_rgb`, `kelvin_to_hex`: the Tanner Helland piecewise fit to Charity's blackbody table. Output is 8-bit sRGB clamped to 1000–40 000 K. |
| `unisimu/state.py` | `SimState`: view routing (shelf/detail), user controls, and a background `tick_loop` at 20 Hz that advances the cinematic clock and applies `evolve()`. |
| `unisimu/components/star_scene.py` | `StarScene(rx.NoSSRComponent)` wrapping `assets/star_scene.jsx`. Pins `three@0.185.1`. Props: `radius, color, stage, luminosity, progress`. |
| `unisimu/components/viewport.py` | Binds those props to `SimState.radius_rsun, color_hex, stage, luminosity_lsun, stage_progress`, and adds the caption overlay. |
| `assets/star_scene.jsx` | 1061 lines of vanilla Three.js. The scene is built once, then a per-frame state machine reads `container._uniSimuLatest` (the last props) and drives every object. |
| `unisimu/presets.py` | Six presets (key, name, mass, blurb, spectral class). |
| `unisimu/hr_geometry.py` | H-R diagram geometry from `evolution_track`. |

### Tick payload (Python → browser, every tick)
**Base vars set in `tick_loop`:**
- `age_years`, `stage`, `radius_rsun`, `temperature_k`, `luminosity_lsun`, `color_hex`, `stage_progress`
- `event_flag` (`"entered_<stage>"` on a transition, otherwise `""`)
- `caption_title`, `caption_text`, `caption_persistent` (when a caption shows or clears)
- `playing` (set False when the star reaches a terminal stage)

**Computed vars that change per tick:** `age_display`, `is_terminal`, `temperature_display`, `luminosity_display`, `radius_display`, `stage_progress_pct`, `current_stage_index`, `hr_marker_xy`.

**Computed vars that depend only on mass:** `hr_track_svg`, `hr_t_ticks`, `hr_l_ticks`, `stage_track_list`, `mass_display`.

**Backend-only, never sent:** `_screen_seconds`, `_run_id`, `_n_loops_running`, `_caption_until`.

**Contract to keep (constraint 4):** the five JS props above, the `StellarSnapshot` fields (`stage, radius_rsun, temperature_k, luminosity_lsun, color_hex, stage_progress`) and these var names.

---

## 2. What the model actually outputs per preset
Sampled with `evolve()` across each `phase_schedule()` segment, 400 points per segment.

| Preset | M (M☉) | Track | MS T (K) | MS L (L☉) | Peak R (R☉) | Remnant |
|---|---|---|---|---|---|---|
| Proxima | 0.12 | proto → MS → red giant → PN → WD | 3050 | 1.75e-3 | **4.31** (red giant) | WD 25 000 K, 0.0505 L☉ |
| Sun | 1.0 | same | 5778 | 1.0 | 103 | WD 25 000 K, 0.0505 L☉ |
| Sirius A | 2.1 | same | 9226 | 20.1 | 163 | WD |
| Betelgeuse | 16.5 | proto → MS → RSG → SN → NS | 30 553 | 2.74e4 | 705 (SN photosphere 4150) | NS 1e6 K, 0.259 L☉ |
| Rigel | 23.0 | proto → MS → RSG → SN → BH | 34 476 | 7.36e4 | 1150 | BH, L = 0 |
| Eta Carinae | 90.0 | same as Rigel | 47 000 | 2.88e5 | 2280 | BH, L = 0 |

Findings the brief did not anticipate:
- **The protostar is mass-independent.** Every preset starts at R 0.16–0.25 R☉, T 2000–3500 K and L 1e-4–4e-4 L☉, including Eta Carinae.
- **Massive-star lifetimes stop depending on mass.** Above 20 M☉ the code uses L = 3200·M, so t_MS = 10¹⁰·M/L = 3.1 Myr for every mass: Rigel and Eta Carinae live equally long.
- **The supernova** peaks at 3e9 L☉ and 60 kK, with the photosphere reaching about 4150 R☉. All of it is keyframed on `stage_progress`.

---

## 3. Visual constants in `assets/star_scene.jsx`
"Derived" means the value comes from the snapshot props. "Invented" means it was chosen by eye.

### Colour pipeline
- `THREE.Color(color_hex)` converts the sRGB hex to linear (Three's colour management is on by default).
- The scene renders into a HalfFloat target with 4× MSAA (:608), runs `UnrealBloomPass`, then `OutputPass` does the linear→sRGB encode.
- `renderer.toneMapping` is never set, so it stays at `NoToneMapping`: HDR values above 1 are clipped at output.
- Brightness is **not derived from luminosity**. It comes from per-stage `intensity` constants. Luminosity only nudges the corona, through `lumBoost`.

| Group | Constants | Derived / invented |
|---|---|---|
| Background | `SPACE_COLOR 0x03040a` (:32) | invented |
| Size mapping | `visualScale`: 0.72·r^0.33 below 1 R☉; log1p(r)·0.6 + 0.3 above; soft cap at 2.5 + 1.2 (:46-52) | derived from R, with an invented curve |
| Rotation | `ROTATION_SPEED_BY_STAGE` 0.02–6.0 rad/s (:59-69) | invented |
| Surface | `SURFACE_BY_STAGE` cell 2.0–7.0, contrast, spots, rays, intensity 0–2.0, blotch (:74-84) | invented |
| Limb darkening | linear law, `uLimb = 0.65` constant (:397, :173), plus a reddening factor (1, 0.72, 0.5) toward the limb (:180) | invented |
| Granulation | fbm at `p` and `2.6p`, mixed 65/35; smoothstep 0.30–0.72; lane colour ×(0.9, 0.72, 0.6) (:166-177) | invented |
| Spots | fbm ×1.7, smoothstep 0.62–0.78, darken ×(1 − 0.7·spot) (:169-176) | invented |
| Corona | quad half-size 5 R (:656); glow = exp(−10d)·0.9 + exp(−3.8d)·0.16; streamers; `lumBoost = clamp(0.7 + 0.06·log10 L, 0.45, 1.1)` (:903) | luminosity-modulated, otherwise invented |
| Bloom | `UnrealBloomPass(256², strength 0.55, radius 0.3, threshold 0.88)` (:612); strength + 0.6·flash + 0.2 if black hole (:1002) | invented |
| Pulsation | 1 + 0.03 sin(1.7t) + 0.012 sin(4.3t), wall clock (:881) | invented (≈3.7 s period) |
| Starfield | 1100 field + 2400 band stars, shell radius 70–100, 5-colour palette with weights, brightness 0.35 + rand³·1.9, size 1.4 + rand⁴·3.4, **twinkle 0.82 + 0.18 sin(…)** (:459-512, :322) | invented, `Math.random` |
| Supernova | collapse p < 0.05 to radius 0.45; burst 0.45 + 2.2·ease; flash rises over 0.05–0.08 then decays as exp(−16(p − 0.08)); shock 0.5 + 7·ease; 3200 ejecta with `uMax 8`; remnant 0.5→6.5; camera shake 0.12·flash (:852-863, :921-957, :1030) | invented timing on `stage_progress` |
| Planetary nebula | shell 0.8→5.0 easeOutCubic, opacity smoothstep 0–0.2, palette teal (0.2, 0.85, 0.78) / pink (1.0, 0.28, 0.42) (:87, :944) | invented |
| Neutron star | radius 0.075 fixed (:91); beams length 6, base 0.55, tilt 0.6; strobe 0.7 + 2.6·align¹⁰ (:691-703, :910) | invented |
| Black hole | horizon 0.6 fixed (:90); disk ring 1.0–3.2, tilt π/2 − 0.42, spin 2.2, doppler 0.55, ×1.7·displayRadius; lens billboard ×6, ring at 1.12, arcs \|sin θ\|^1.4 (:271-317, :729-740, :994) | invented; shown for **every** black hole |
| Protostar | dust disk 1.0–4.4, spin 1.6; jets length 3.2 (:706-725) | invented (protostar stays stylized per brief) |
| Camera | FOV 50, start (0, 1.2, 6), orbit 2–26, autoRotate 0.35; auto-zoom clamp(3 + frame·2.3, 2.6, 22) (:603-623, :1013) | invented framing (fine: camera, not physics) |

**Sources of randomness:**
- `Math.random()` is used for the starfield (:463-512), ejecta seeds (:534-540), nebula seed (:420) and camera shake (:1031).
- All animation runs on wall-clock `performance.now()` (:821).

**Consequence:** no two loads render the same pixels. See risk R1.

---

## 4. Hypotheses from the brief

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | The starfield twinkles | **Confirmed** | `vTwinkle = 0.82 + 0.18·sin(uTime·(0.6 + aPhase·1.7) + aPhase·40)` (:322) |
| H2 | Every high-mass star gets a lensed, Doppler disk | **Confirmed** | `blackHoleDisk` and `lens` fade in whenever `stage === "black_hole"` (:990-998). Lensing is a billboard with an invented ring radius; nothing is ray traced. |
| H3 | Corona and bloom tuned by eye | **Confirmed** | §3 corona and bloom rows |
| H4 | Constant limb darkening, one granulation scale | **Confirmed**, partly | The limb law is linear with constant 0.65. Granulation scale varies by *stage* (2.0–7.0) but not with T, g or R. |
| H5 | `blackbody.py` is an 8-bit sRGB fit | **Confirmed** | Helland fit, int 0–255, clamped at 40 kK. No CIE path, no linear output. |
| H6 | Issue #11: Proxima swells to ~4 R☉ | **Confirmed** | Red giant up to 4.31 R☉ (§2) |
| H6 | Issue #12: white dwarf frozen at 25 000 K, 0.05 L☉ | **Confirmed** | 25 000 K, 0.012 R☉, so L = 0.0505 L☉ forever |
| H7 | Giants "cool to ~3000 K", the Sun reaches "~100 R☉" | **Partly** | The red-giant tip is **3200 K** (`stellar.py:40`); the Sun reaches 103 R☉. Check against MIST in Phase 7. |
| — | Test count "122" | **Corrected** | 128 tests pass (43 functions, parametrized) |

---

## 5. Baseline

### Tests
`pytest tests/ -q` gives **128 passed** (0.45 s) at commit `0557778`.

### Screenshots and console
Captured with `tests/visual/capture_baseline.py`: headless Chromium using SwiftShader, at 1440×900, 1× speed.
The script pauses the simulation for each frame. Images are in `tests/visual/baseline/<preset>/NN_<stage>.png` and the details in `report.json`.

**Result:** 30/30 frames, every stage of every preset.
- At 16×, all six presets ran through their full expected stage track.
- The only console message was the known **issue #9** (`<svg> attribute height: Expected length, "auto"`), three times per preset. Nothing new.

**What the frames show:**

| Stage | Observation | Relevant phase |
|---|---|---|
| Protostar | Identical for all six presets: orange star, dust disk and jets. | Stays stylized (brief) |
| Main sequence | Colour goes peach (Proxima, 3050 K) → white (Sun) → blue-white (Sirius). Betelgeuse, Rigel and Eta Carinae look almost the same, because the colour clamps at 40 kK and size saturates. **Every star has a corona of long rays several radii wide that washes out the background.** A red dwarf reads as bright as the Sun. | 1 (exposure), 3 (corona) |
| Red giant / supergiant | Captured at about 55 %, giants are cream-peach. **Supergiants are still blue-white**, because T moves geometrically from the MS value toward 3500 K and only reaches red near the end of the stage. | 7 (tracks) |
| Planetary nebula | A teal/pink fbm shell fills the view, with a blue-white core and a large corona. | 5 |
| Supernova (about 53 %) | A dark ball inside a bright blue-white shell with orange clumps. The body intensity has already faded, so it reads as an eye or shell rather than a fireball. | 5 |
| White dwarf | A point-like blue-white core inside the lingering shell. | 5, 7 (cooling) |
| Neutron star | Two bright illustrative beams inside the remnant shell. | 5 |
| Black hole | A small disc with a photon ring and a bright one-sided disk inside the remnant shell. | 4 |

Caption overlays (stage text) appear in frames taken soon after a stage change, because they sit on top of the canvas.

**Frame time** (main sequence, 3 s sample) was 209–429 ms mean and 300–933 ms p95. That is SwiftShader on the CPU, so it is **not** comparable with the 60 fps GPU budget (R2). Measure real frame times in a normal Chrome window per phase.

**Incident during capture: issue #14 reproduced, with the mechanism.**
1. With `reflex run` active, I created or edited files in the repo (`tests/visual/capture_baseline.py`, this note). This was outside `assets/`.
2. Reflex hot-reloaded and re-ran `npm install`.
3. npm failed with `EBUSY: resource busy or locked, copyfile …\.web\node_modules\@rolldown\binding-win32-x64-msvc\rolldown-binding.win32-x64-msvc.node`.
4. Then: `[ERROR] Unexpected exit from worker-1`. The frontend still served pages, but the backend was dead, so clicking a preset did nothing.

So the rule is broader than issue #14 says: **don't touch any file in the project while `reflex run` is active.** The locked native binary is consistent with OneDrive or the running Vite holding the file open. Worth adding to the issue.

**Data not committed:** the baseline PNGs (11 MB) and `report.json` are left untracked until you approve committing them. Alternatives are Git LFS or keeping them local.

---

## 6. Proposed phase order and risks

| Phase | Depends on | Main risk | Mitigation |
|---|---|---|---|
| 1 Radiometry | — | Tone mapping changes stylized output | All new code behind `render_mode == "physical"`; stylized keeps `NoToneMapping` and today's path |
| 2 Starfield | 1 | **Data licence (D4)**; asset size | Ask before committing the HYG-derived binary; keep it under 1 MB with a magnitude cut |
| 3 Surface | 1 | Cool-star limb-darkening table not yet verified; supergiant granule factor | Open Claret & Bloemen's ReadMe first; cite the factor or flag it |
| 4 Black hole | 1, 2 | Hardest phase: lookup textures in WebGL; frame time | Bruneton's precomputed tables; quality tier controls their resolution |
| 5 Death scenes | 1, 6 | Needs the supernova sub-clock from Phase 6 | Do Phase 6 first, or define the mapping inside Phase 5 |
| 6 Time honesty | — | Small; touches telemetry only | Additive vars |
| 7 MIST (optional) | — | Licence ("All rights reserved", D6); changes existing stage tracks (old tests) | Ask; keep it behind a flag |

**Suggested order:** 1 → 2 → 3 → 6 → 5 → 4 → (7).
- Time honesty moves before the death scenes, because the supernova needs its day clock.
- The black hole moves last of the core phases. It is the riskiest, and it reuses the Phase 2 starfield.

**Cross-cutting risks:**
- **R1 Non-deterministic rendering.** `Math.random` and wall-clock time mean screenshots can't be compared exactly, even in stylized mode.
  - Proposal for Phase 1: add an optional, test-only URL flag `?seed=…&freeze=t` that seeds the RNG and pins `elapsed`. It defaults off, so behaviour stays unchanged.
  - Until then, stylized "pixel-identical" checks (verification item 3) can only be tolerance-based.
- **R2 Software-rendered baseline.** Headless Chromium uses SwiftShader. Frame times here measure the CPU, not the integrated-GPU budget (constraint 9). Measure real frame times in a normal Chrome window at each phase.
- **R3 OneDrive (issue #14).** Reflex itself warns at start-up: "Creating project directories in OneDrive may lead to performance issues". Never edit `assets/` while `reflex run` is active. Moving the repo is the owner's call.
- **R4 Existing tests.** Phases 7 and #11 will change `stage_track` for Proxima, which existing tests may pin. Stop and ask (constraint 8).

## New dependencies in this phase
- `playwright` 1.63.0 (Python) plus the Chromium build it downloads. Dev only, used by `tests/visual/capture_baseline.py`. It was installed into `venv/` and is not added to `requirements.txt`; where to record it (e.g. `requirements-dev.txt`) is left for the owner.

## How to reproduce
```powershell
reflex run                                   # terminal 1
venv\Scripts\python tests\visual\capture_baseline.py   # terminal 2, about 10 minutes; edit nothing meanwhile
venv\Scripts\python -m pytest tests -q
```
