# Phase 4: The black hole, done properly

Branch `realism/phase-4-black-hole`. Equations and sources are in [`equations/04-black-hole.md`](equations/04-black-hole.md); §8 lists everything verified for this phase.

## Why it was needed
The stylized black hole was three tricks stacked:
- a black ball (the "horizon");
- a camera-facing picture of a glowing ring at an invented radius;
- a bright, Doppler-tinted accretion disc around **every** black hole.

None of it bent light. An isolated stellar black hole like the one Sahu et al. (2022) found has no luminous disc at all: it is dark, and visible only through its gravity.

## The physics

### Light bends, and some of it falls in
Around a non-rotating mass M (units G = c = 1), a light ray's path in its plane obeys the photon orbit equation

u″ + u = 3Mu², with u = 1/r and ′ = d/dφ.

The "3Mu²" term is general relativity's addition to a straight line. Far away it gives the famous weak-field bending of 4M/b for a ray passing at impact parameter b. Close in, it lets light orbit the hole: at r = 3M (the **photon sphere**) light can circle indefinitely. Rays aimed within b < b_c = 3√3 M ≈ 5.196 M spiral in through the **horizon** at r = 2M and never come out. Those rays make the **shadow**.

From a finite distance r_O, the shadow's angular radius is **Synge's formula**:

sin α_sh = 3√3 M √(1 − 2M/r_O) / r_O.

### How the picture is made: ray tracing, per pixel
Each pixel of the physical-mode sky is a light ray traced **backwards** from the camera:
1. Take the camera's position and the pixel's direction. The angle α from the outward radial direction gives the starting slope, u′ = −u √(1 − 2Mu) cot α.
2. Integrate u″ = 3Mu² − u with 4th-order Runge–Kutta in φ. The step count follows the quality tier: 240, 160 or 96 steps over 2.5π.
3. If u reaches 1/(2M), the ray came from the horizon, so the pixel is **black**.
4. If u reaches 0, the ray escaped to infinity. Its outgoing direction (cos φ, sin φ in the ray's plane) looks up the **unlensed sky**, which is rendered once into a cube map (catalogue stars and glow).
5. *(Companion scenario only)* If the ray crosses the disc plane between the ISCO (6M) and the outer edge, the pixel shows the disc's light (below).

The same integrator lives in Python as `relativity.trace_ray`, and the tests run it. The two agree because they are the same arithmetic.

**What you see** is real strong lensing:
- a sharp black shadow;
- background stars stretched **tangentially** into arcs;
- a compressed, lensed copy of the whole sky in a ring around the shadow.

### The disc, only with a companion (decision D2)
Turn on **"Black hole with a companion"** to add a thin accretion disc from the ISCO (6M) to 20M:
- **Temperature:** T⁴ ∝ r⁻³(1 − √(r_in/r)), peaking at r = 49/36 r_in. The peak is a scenario value of 10⁷ K, an X-ray-binary-like order of magnitude (**unverified**).
- **Shift:** each disc point is seen with frequency shift g = √(1 − 3M/r) / (1 − Ωλ) / √(1 − 2M/r_cam), with Ω = √(M/r³) and λ the photon's angular momentum about the disc axis (from the traced ray). That combines gravitational redshift, the moving gas's time dilation, the Doppler shift of the approaching and receding sides, and the camera's own blueshift.
- **Colour:** by Liouville's theorem (I_ν/ν³ is conserved), a shifted blackbody **is** a blackbody at **gT**. So the shader looks up the Phase 1 blackbody colour and visible luminance at gT from a 64-entry table built in Python. Bolometrically that is a factor g⁴. At 10⁷ K the visible band sits on the Rayleigh–Jeans tail, so the *visible* asymmetry is closer to g. The tests show both.
- **Close in, gravity wins.** At r = 8M even the approaching side is redshifted (g = 0.97). It is still 4.4× brighter, bolometrically, than the receding side.

## Verified end to end, on a GPU
`tests/visual/render_scenarios.py` (new) loads the real scene module in headless Chromium without Reflex, feeds it props from the real Python physics, and checks every shader compile.

| Check | Result |
|---|---|
| Console errors across 11 scenarios (every stage, both looks, coronagraph, disc) | **0**. Every shader compiles, including the Phase 3 star shader that stylized mode also uses. |
| Rendered shadow radius at r = 29M | **113.0 px**, against Synge's **112.3 px** (within one pixel) |
| Shadow error from the 2.5π φ budget | about 0.05° at any step size from 0.01 to 0.08 rad, under one pixel |

The first run also caught two real problems:
- **The glow** (from Phase 2) rendered as brown streaks. It is fixed: smoothing is now flux-conserving in both axes and the boost dropped from 150 to 50 (see 02-starfield.md).
- **The companion disc** filled half the screen. A 20M disc seen from 29M really does span about ±34°. With the disc on, the camera now frames its outer edge, and auto exposure puts the disc peak at 0.35 rather than saturating it.

**These two fixes have not been re-rendered.** The harness's file server was stopped for low memory before the re-run.

## What changed
| File | Change |
|---|---|
| `unisimu/physics/relativity.py` | **New.** Characteristic radii, `shadow_angular_radius` (Synge), `impact_parameter`, `trace_ray` (RK4 twin of the shader), `deflection_angle`, `circular_orbit_redshift`, `disk_temperature`, `bolometric_intensity_ratio`, `blackbody_color_table`. |
| `assets/star_scene.jsx` | Physical black hole: a sky cube map (sky objects on their own layer) and a lens sphere whose fragment shader ray-traces each pixel. The stylized horizon, fake lens and disc are hidden in physical mode. The quality tiers gained ray-march steps and cube size. **Stylized unchanged.** |
| `state.py`, `star_scene.py`, `viewport.py`, `controls.py` | **Added** `bh_disk` (default off) and the "Black hole with a companion" switch; constant props `bh_params` and `bh_color_table`. |
| `tools/build_starfield.py`, `assets/starfield.bin` | Glow smoothing fix (Phase 2 follow-up). |
| `tests/test_relativity.py` | 14 new tests. |
| `tests/visual/render_scenarios.py` | **New** shader and scene harness (output gitignored). |

## Known simplifications
- **No spin.** The Kerr (spinning) case is out of scope, as the brief says; reference: James et al. 2015.
- **Display scale.** The horizon is drawn at the stylized display size (0.6 scene units), and M is set from it. The geometry depends only on r/M, so the *picture* is exact for that ratio, but the true horizon (~20 km for a 7 M☉ remnant) is far smaller than shown.
- **Static camera.** The camera is treated as a static observer; its orbital motion (aberration) is ignored.
- **Sky resolution.** Point stars in the cube map are at the cube's resolution. At tier 0 that is about 1.6× blurrier than the screen, and stars are a little brighter after sampling.
- **Non-sky objects aren't lensed.** Objects that aren't part of the sky (illustrative remnant shells) are drawn unlensed on top.
- **Captured-ray tolerance.** Rays still circling after 2.5π are treated as captured, which makes the shadow edge about 0.05° too large.
- **Disc model.** The disc is optically thick, thin and blackbody, with a simplified temperature profile, and has no higher-order images beyond what the integrator finds within the φ budget.

## How to verify by hand
1. Choose **Look → Physical**, then play **Rigel** or **Eta Carinae** to the end.
2. **The shadow:** a sharp black disc. Background stars near it are stretched along circles, and the whole sky looks squeezed into a ring around it.
3. Orbit the camera (drag). The lensed sky slides and distorts, but the shadow stays round.
4. Turn on **Black hole with a companion**:
   - the camera steps back;
   - a blue-white disc appears around the shadow;
   - its image is warped over the top of the shadow (light from the far side of the disc, bent toward you);
   - one side is brighter than the other.
5. Switch to **Stylized**: the old look returns unchanged.
6. Optional: `venv/Scripts/python tests/visual/render_scenarios.py` with `reflex run` **stopped**. Expect 0 console errors and a shadow radius within a pixel of Synge's.

## Tests
`pytest tests/ -q` gives **225 passed** (211 before this phase, plus 14 new):
- the characteristic radii;
- the traced shadow edge equals Synge's formula at 10, 30 and 100 M, and the edge ray's impact parameter equals b_c;
- weak-field bending is 4M/b, and bending grows toward the photon sphere (past 90° near b_c);
- rays inside and outside the shadow fall in and escape respectively, and disc-plane crossings are found;
- g → 1 far away;
- face-on ISCO light has g = 1/√2;
- the approaching side is g⁴ brighter, and a static observer sees an extra blueshift;
- the disc temperature profile peaks where expected and falls off as r^(−3/4);
- the colour table runs from red to blue with rising luminance.

## References (opened)
- Perlick & Tsupko (2022), black hole shadows review: https://arxiv.org/abs/2105.07101
- Bruneton (2020), real-time non-rotating black holes: https://arxiv.org/abs/2010.08735
- Sahu et al. (2022), an isolated dark black hole: https://arxiv.org/abs/2201.13296
- James et al. (2015), Kerr reference for a later pass: https://arxiv.org/abs/1502.03808
