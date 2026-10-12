# Phase 7: Stellar tracks and remnants (issues #11 and #12)

Branch `realism/phase-7-tracks` (stacked on `realism/phase-4-black-hole`). Equations and sources are in [`equations/07-tracks-remnants.md`](equations/07-tracks-remnants.md).

**Decision D6:** MIST's site says "All rights reserved", so **no MIST data is in the repo**. The owner chose to fix #11 and #12 with physics that is already verified, and to keep MIST as an optional, local-only extra.

## Issue #11: Proxima Centauri no longer becomes a red giant

### Why
Before this phase, every star below 8 M☉ became a red giant. Proxima (0.12 M☉) swelled to **4.3 R☉**. Real red dwarfs can't: they stay **fully convective**, so convection keeps stirring fresh hydrogen into the core. That lets them burn nearly all of their fuel over trillions of years. They never build the inert, compressed core that makes a star swell into a giant.

### The physics (Laughlin, Bodenheimer & Adams 1997, full text opened; Adams et al. 2004)
| Mass | What the 1997 models show |
|---|---|
| 0.10 M☉ | Stays convective for 5.74 trillion years, then contracts and **heats to at most 5807 K**, "never … more than ∼1% as bright" as the Sun. Ends as a **helium white dwarf**. |
| 0.16 M☉ | Transitional: radius grows by only 1.6× |
| 0.20 M☉ | Radius grows by 5.1× |
| **0.25 M☉** | **The lowest-mass star that becomes a red giant** |

So below 0.25 M☉ the track is now **protostar → main sequence → blue dwarf → white dwarf**, with no giant and no planetary nebula. The **blue dwarf** stage:
1. **First half:** the star heats from its main-sequence temperature to 5807 K, and its brightness rises to 1% of the Sun's. Since L and T both rise, the radius from Stefan–Boltzmann *shrinks* (Proxima: 0.15 → 0.10 R☉), just as the paper says ("the whole star contracts").
2. **Second half:** it shrinks onto the white-dwarf radius at that peak temperature. This is a simplified version of the paper's "turning the corner" onto the white-dwarf track.

No blue dwarf exists yet: the universe (about 10¹⁰ years old) is far younger than a red dwarf's main sequence. The new caption says so.

## Issue #12: white dwarfs now cool

### Why
A white dwarf was frozen at 25 000 K and 0.05 L☉ forever. A real white dwarf has no fuel left. It shines only by leaking stored heat, so it fades and reddens for billions of years.

### The physics: the Mestel cooling law (Kawaler 1998, Eq. 2.3, opened)
t_cool = 9.41 × 10⁶ yr · (A/12)⁻¹ (μ_e/2)^(4/3) μ^(−2/7) (M/M☉)^(5/7) (L/L☉)^(−5/7).

It uses Kawaler's worked-example values: M = 0.6 M☉, a carbon/oxygen core (A = 14), μ_e = 2, μ = 1.4. Each white dwarf starts at the luminosity the previous stage handed it, and continues along the curve from the point where it already has that luminosity. The radius stays fixed (0.012 R☉), so T follows from Stefan–Boltzmann.

| White dwarf of… | At birth | After 1 Gyr | After 10 Gyr |
|---|---|---|---|
| the Sun | 94 000 K, 10 L☉ | 8 300 K | **3 710 K** |
| Proxima (helium, via the blue dwarf) | 5 807 K, 1.5 × 10⁻⁴ L☉ | — | ~3 400 K |

As a check, Kawaler quotes about 7 Gyr to fade to 10⁻⁴·⁵ L☉. This implementation gives 8.3 Gyr, consistent with the "within 30%" he states for Mestel. The 19% gap remains noted in the equations doc.

### Seeing it in the app
The play loop stops once a star becomes a remnant, and changing that loop is outside this work's contracts. So the telemetry now shows a **"White dwarf cooling: time since it formed"** slider whenever the star is a white dwarf. It runs from 1 year to 10 billion years on a log scale, and temperature, brightness and colour update as you drag. The Time row reads, for example, "1.2 Gyr since it formed".

## MIST: optional and local only
- `tools/build_mist_tracks.py` reads `.eep` track files **you download** from mist.science and writes `data/mist_tracks.json`. Both the data folder and that file are gitignored.
- `unisimu/physics/mist.py` parses them using the layout from MIST's own reader script (`read_mist_models.py`): 11 header lines, initial mass on line 7, and column names after a `#`.
  - It maps MIST phase codes (PMS −1, MS 0, SGB+RGB 2, CHeB 3, EAGB 4, TPAGB 5, post-AGB 6, WR 9) to UniSimu stages.
  - The age column name `star_age` was **not** confirmed by that script, so the parser fails clearly if it's absent.
- It is **not wired into `evolve()`**. That needs a real downloaded track to test against. A comparison test (MIST vs analytic stage order) runs automatically once a local table exists.

## What changed
| File | Change |
|---|---|
| `unisimu/physics/stellar.py` | `RED_DWARF_MASS_THRESHOLD` (0.25), the `RED_DWARF_TRACK` and `blue_dwarf` stage, and blue-dwarf constants (5807 K, 1% L☉). `terminal_flash_years` covers the blue-dwarf fade. White dwarfs cool through `remnants.py` (`WHITE_DWARF_TEMPERATURE_K` is removed). **The signatures of `evolve`, `phase_schedule`, `cinematic_age_years` and `stage_track` are unchanged.** `stage_track` now returns the red-dwarf track below 0.25 M☉; that is the deliberate fix for #11. |
| `unisimu/physics/remnants.py` | **New.** `cooling_time_years` and `cooled_luminosity_lsun` (Mestel). |
| `unisimu/physics/mist.py`, `tools/build_mist_tracks.py` | **New**, optional and local-only. |
| `unisimu/copy.py`, `components/timeline.py` | Blue-dwarf label and caption. |
| `unisimu/state.py`, `components/telemetry.py` | **Added** `remnant_log_age`, `set_remnant_age` and the cooling slider. The remnant time readout now says how long since it formed. |
| `.gitignore` | `data/mist/` and `data/mist_tracks.json`. |
| Tests | `tests/test_remnants.py` (16), `tests/test_mist.py` (6, 1 skipped without data). My own Phase 6 timekeeping test was updated: Proxima's slowest phase is now its protostar. |

No existing (pre-realism) test needed changing: every red-giant test uses 0.3 M☉ or more.

## Known simplifications
- **White-dwarf mass and core.** Every white dwarf uses Kawaler's example (0.6 M☉, carbon/oxygen), even Proxima's, which should be a lighter helium white dwarf. No initial–final mass relation was verified.
- **Mestel's limits.** It ignores neutrino cooling (young, hot white dwarfs cool faster), crystallisation (a pause) and Debye cooling (a faster drop at the faint end).
- **Blue-dwarf details.** The 5807 K peak and 1% brightness come from the 0.10 M☉ model and are applied to every mass below 0.25 M☉; the 0.16–0.24 M☉ "transitional" stars are not modelled separately. The blue dwarf's length, and its shrink onto the white dwarf, are model assumptions.
- **Temperature step for the Sun.** Its white dwarf starts at 94 kK while the planetary-nebula core ends at 100 kK: a 6% temperature step where the two radii differ. Luminosity hands over exactly.

## How to verify by hand
1. Play **Proxima**. The timeline should read Protostar → Main Seq. → **Blue Dwarf** → White Dwarf. It should never show a red giant, and its radius should *shrink* while it heats.
2. At the white dwarf, drag **"White dwarf cooling"** to the right. Temperature, brightness and colour should fall, reaching a few thousand kelvin by 10 Gyr.
3. Play **the Sun**. Its white dwarf should start near 94 000 K and cool the same way.

## Tests
`pytest tests/ -q` gives **247 passed, 1 skipped** (225 before this phase, plus 22 new; the skipped one needs local MIST data):
- below 0.25 M☉: no red giant and no nebula, with the red-dwarf stage order; the threshold sits exactly at 0.25;
- Proxima never exceeds its main-sequence radius (it used to reach 4.3 R☉);
- the blue dwarf peaks at 5807 K and stays at or below 1% L☉;
- Mestel reproduces Kawaler's example within 30% and scales as L^(−5/7);
- cooling starts at the birth luminosity and only fades;
- white dwarfs of three masses cool and redden over 10 Gyr, and hand over continuously from the previous stage;
- a 10-Gyr-old white dwarf is 3000–5000 K;
- MIST parsing, the clear error for a missing age column, phase mapping, interpolation, and the comparison test (skipped without data).

## References (opened)
- Laughlin, Bodenheimer & Adams (1997), ApJ 482, 420: https://iopscience.iop.org/article/10.1086/304125/fulltext/35131.text.html
- Adams, Laughlin & Graves (2004), RevMexAA (SC) 22, 46: https://www.astroscu.unam.mx/rmaa/RMxAC..22/PDF/RMxAC..22_adams.pdf
- Kawaler (1998), Mestel cooling: https://arxiv.org/abs/astro-ph/9802217
- Choi et al. (2016), MIST I: https://arxiv.org/abs/1604.08592. MIST: https://mist.science. Reader script: https://github.com/jieunchoi/MIST_codes (`scripts/read_mist_models.py`)
