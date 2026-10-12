# Phase 2: Starfield without the lie

Branch `realism/phase-2-starfield`. Equations and sources are in [`equations/02-starfield.md`](equations/02-starfield.md).

## Why it was needed
The background sky had two problems:
- **It twinkled.** Each star's brightness was multiplied by `0.82 + 0.18·sin(t·…)`. But twinkling (scintillation) is Earth's turbulent atmosphere bending starlight. Seen from space, stars are perfectly steady points.
- **It was invented.** About 3500 random points were drawn from a 5-colour palette, so no constellation was real and no colour meant anything.

The sky is the largest area on screen, so making it real is the cheapest big gain in realism.

## The physics
1. **Where the stars are.** Each catalogue position (RA α, Dec δ) becomes a unit vector, (cos δ cos α, cos δ sin α, sin δ). The scene axes put the north celestial pole "up". The mapping (x, y, z) → (x, z, −y) keeps the frame right-handed, so constellations aren't mirror-imaged (a test checks this).
2. **How bright.** Magnitudes are logarithmic. Pogson's definition gives the flux ratio f/f₀ = 10^(−0.4(m − m₀)), so 5 magnitudes is exactly a factor of 100. Sirius (V = −1.44) is 3.77× a V = 0 star, and the faintest star kept (V = 6.5) is 0.0025×.
3. **What colour.** Each star's B−V colour index becomes a blackbody temperature through Ballesteros (2012), Eq. 14:
   T = 4600·(1/(0.92(B−V)+1.7) + 1/(0.92(B−V)+0.62)).
   That temperature then goes through the Phase 1 pipeline (Planck → CIE → linear sRGB). The same colour science now covers the star you're watching and every star behind it.
4. **How big.** A star is far too small to resolve, so its apparent size comes from the *camera*, not the star. Each star is drawn as the camera's point-spread function: a Gaussian core (σ = 0.9 px) whose peak is flux × exposure. Bright stars look bigger only because more of their core saturates. There is **no time term at all** in the catalogue-star shader.

## What changed
| File | Change |
|---|---|
| `unisimu/physics/starfield.py` | **New.** `bv_to_temperature` (Ballesteros), `relative_flux` (Pogson), and `equatorial_unit_vector` / `equatorial_to_scene` / `scene_direction`. |
| `tools/build_starfield.py` | **New offline tool** (standard library only). Reads `hygdata_v42.csv.gz` and writes `assets/starfield.bin`: 8920 stars (V ≤ 6.5) sorted brightest first, plus a 128×64 sky-glow map from the 6.5 < V ≤ 9 stars. 340 KiB in total. |
| `assets/starfield.bin` | **New data**, CC BY-SA 4.0 (decision D4). Credited in `assets/starfield.LICENSE.md`, the README's "Third-party data" section, and the in-app Legend & Help. |
| `assets/star_scene.jsx` | **Physical mode** loads the binary and draws steady catalogue stars plus the glow sphere. If the file is missing or still loading, the procedural sky shows instead, with **twinkle off**. **Stylized mode is unchanged** (twinkle on, same procedural sky). New: an automatic **quality tier** that drops to V ≤ 5.5, then V ≤ 4.5, when frames average more than 25 ms over 3 s. It only ever steps down, and logs `[UniSimu] … quality tier N` to the console. |
| `.gitattributes` | `*.bin binary`, so git never line-ending-converts the packed floats. |
| `tests/test_starfield.py` | 16 new tests (below). |

## The Milky Way: what's real and what isn't
The band is drawn from the *real* catalogue: the fainter stars (6.5 < V ≤ 9) are summed per sky cell and divided by the cell's solid angle, giving brightness per steradian.

Near the poles each equirectangular cell covers a much smaller solid angle, so one star made a bright spike there. The builder therefore averages over about 1/cos δ columns. A test checks that total flux is conserved.

Its brightest region falls at RA ≈ 11.4 h, Dec ≈ −60°: Carina and Crux, the bright southern Milky Way.

**However**, most of the Milky Way's light comes from stars far fainter than V = 9. At the stars' own exposure, the stars we have would make a glow too faint to see. `GLOW_UNRESOLVED_BOOST = 150` stands in for the missing unresolved stars. **That factor is an approximation, not a measurement**, and the in-app credit says so.

The glow is matched to the stars' energy scale: one unit of flux spread as glow carries the same total pixel energy as one unit of flux in a star's PSF.

## Update from Phase 4
The first real render, in the Phase 4 shader harness, showed the glow as brown horizontal streaks, which was wrong. Two changes fixed it:
- **Smoothing.** The builder smoothed only along RA. It now scatters each cell's *flux* evenly over a ±2-row patch that widens toward the poles, then divides by solid angle. Total flux is still exactly conserved (tested).
- **Boost.** `GLOW_UNRESOLVED_BOOST` was 150, which was too strong. It is now **50**.

`assets/starfield.bin` has been rebuilt with the new smoothing.

## Known simplifications
- **Sky exposure is independent of the star's exposure.** A real camera exposed for a nearby star's surface would record a **black sky**: background stars are many orders of magnitude fainter. The sky uses its own fixed exposure (`SKY_EXPOSURE`, chosen so that V = 6.5 stars are at the edge of visibility). This is a deliberate presentation choice.
- **Brightness is V-band, not bolometric.** HYG's `mag` is visual magnitude, which suits a picture.
- **Colour is a blackbody approximation.** Ballesteros' formula is a blackbody fit and ignores absorption lines; M stars may be off by a few percent in T. The 1891 stars with no B−V, and those clamped to B−V ∈ [−0.4, 2.0], get 5772 K and the edge values respectively.
- **We see the Sun's sky.** The positions are as seen from the Sun. For a star a few parsecs away the sky barely changes, but for Betelgeuse (about 200 pc away) it would look different. No parallax is applied.
- **No diffraction spikes.** They are a telescope artefact, so they're off.

## How to verify by hand
1. Run `reflex run`, open a preset, and choose **Look → Physical**.
2. **No twinkle.** With the mouse still, watch any bright background star for 10 s; its brightness should not change. Switch to **Stylized** and the twinkle comes back.
3. **Real constellations.** Orbit the camera (drag) until Orion is in view: the three Belt stars, Betelgeuse orange and Rigel blue-white. Sirius should be the brightest point on the sky, below and to the left of Orion's belt.
4. **Credits.** Open **Legend & Help** and check the data credit at the bottom.
5. **Fallback.** Rename `assets/starfield.bin` with the server **stopped** (issue #14), then restart. Physical mode should show the procedural sky without twinkle, and the console should say `catalogue starfield unavailable`.

## Tests
`pytest tests/ -q` gives **164 passed** (148 before this phase, plus 16 new):
- B−V → T matches Ballesteros at six values and decreases monotonically;
- 5 mag = ×100;
- the scene axes put the pole up and are right-handed;
- the builder sorts brightest first, keeps directions as unit vectors and colours at unit luminance, gives a neutral colour when B−V is missing, and conserves flux in the glow;
- in the shipped binary, Sirius and Canopus are first and second, with directions within 10⁻³ and a flux ratio of 10^(0.4×0.82) = 2.13.

## Visual check
**Not yet done in a browser.** The machine had about 0.5 GB free and the Claude-in-Chrome extension wasn't connected, so neither headless capture nor driving Chrome was possible.

Use the checklist above, or ask for a capture once memory is free. This is tracked, together with Phase 1's open screenshot items, in [README.md](README.md).

## New dependencies
None. The build tool uses only the Python standard library; pandas and astropy weren't needed.

## References (opened during research and this phase)
- HYG Database v4.2, licence and field list: https://www.astronexus.com/projects/hyg and https://www.astronexus.com/projects/hyg-details. Repository: https://codeberg.org/astronexus/hyg
- Ballesteros (2012), EPL 97, 34008: https://arxiv.org/abs/1201.1809
- IAU 2015 Resolution B2 (the magnitude scale): https://arxiv.org/abs/1510.06262
- CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/
