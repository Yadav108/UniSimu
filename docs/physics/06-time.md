# Phase 6: Time honesty

Branch `realism/phase-6-time`. The bookkeeping is described in [`equations/06-time.md`](equations/06-time.md).

## Why it was needed
A star's life spans an absurd range of timescales: a red dwarf burns hydrogen for about 10¹² years, and a supernova's light changes over days. The app plays every life in about 50 seconds. To do that, `phase_schedule()` gives each of the four phases a **fixed** screen time (6 s, 20 s, 14 s, 10 s) and maps the phase's real duration linearly onto it.

That's a good cinematic choice, but it hides something important: **the clock rate jumps between phases.** Watching the Sun, one second on screen is 500 million years during the main sequence, then 200 years during the planetary-nebula flash. For Proxima the main sequence runs at 34 billion years per second, about 4 million times faster than its slowest phase. Before this phase the only readout was the age, so nothing told you that.

The animations have a similar problem. Spin, pulsation, drifting spots and expanding gas run on wall-clock seconds, so their speed means nothing physical.

## What it does (decision D5: readouts only)
The brief offered two options: a readout, or a slow "true rate" mode. The default, D5, is **readout only**, so the cinematic clock itself is unchanged.

The telemetry gains a **Time** section:

| Row | Meaning | Example (Sun, mid main sequence, 1×) |
|---|---|---|
| In this stage | Real time since the current timed phase began, out of its real length | `5 Gyr of 10 Gyr` |
| Clock rate | Real time per screen second, at the chosen playback speed | `1 s = 500 Myr` |
| *(note)* | The clock speeds up and slows down by up to a few million times, and on-screen motion is cinematic | — |

Once the star reaches its remnant (white dwarf, neutron star or black hole), the simulation stops, so the rows read "remnant (clock stopped)" and "stopped".

The physical periods that do exist are already shown next to their animation: Phase 3 added the **pulsation period** row for giants (e.g. Betelgeuse ≈ 392 d). The animation itself is labelled cinematic.

## The arithmetic
For a phase with real span [a₀, a₁] played over s screen seconds, at playback speed k:
- clock rate = k · (a₁ − a₀) / s, in years per screen second;
- time in the stage = age − a₀.

Both read directly from `phase_schedule()`, so the readout can't disagree with what the simulation does.

| Preset | Fastest phase (main sequence) | Slowest phase (terminal flash) | Ratio |
|---|---|---|---|
| Proxima (0.12 M☉) | 34.2 Gyr/s | 8.33 kyr/s (protostar) | 4.1 × 10⁶ |
| Sun (1 M☉) | 500 Myr/s | 2.1 kyr/s (planetary nebula) | 2.4 × 10⁵ |
| Betelgeuse (16.5 M☉) | 301 kyr/s | 40 d/s (supernova) | 2.8 × 10⁶ |

*(Updated in Phase 5: the terminal phase now lasts as long as it really does, 400 days for a supernova and 21 kyr for a planetary nebula, instead of a fixed 2000 years. Updated again in Phase 7: Proxima now becomes a blue dwarf, with no planetary nebula, so its slowest phase is the protostar.)*

## What changed
| File | Change |
|---|---|
| `unisimu/physics/timekeeping.py` | **New.** `StageClock`, `stage_clock(mass, age)` and `compression_range(mass)`. |
| `unisimu/formatting.py` | **Added** `format_duration(years)` (d / yr / kyr / Myr / Gyr). `format_scientific` is unchanged. |
| `unisimu/state.py` | **Added** computed vars `stage_time_display` and `clock_rate_display`. Nothing existing changed, and the tick loop is untouched. |
| `unisimu/components/telemetry.py` | **Added** the Time section and the cinematic-clock note. |
| `tests/test_timekeeping.py` | 19 new tests. |

No JS changes and no new dependencies.

## Known simplifications
- Within a phase the clock is linear, so the readout is exact. *Across* the phases the speed jumps abruptly at each boundary; that's how the existing model works, and it's now visible rather than fixed.
- The terminal flash for massive stars is still 2000 years long. Phase 5 replaces the supernova timing with a light curve measured in days, mapped onto the same 10 screen seconds, and this readout will report it automatically.

## How to verify by hand
1. Pick **The Sun** and press Play at 1×. During the main sequence, *Clock rate* should read `1 s = 500 Myr`, and *In this stage* should count up to `10 Gyr of 10 Gyr`.
2. Switch to 16×: the rate becomes `1 s = 8 Gyr`.
3. At the planetary nebula the rate drops to `1 s = 2.1 kyr`, a 240 000-fold slowdown that was invisible before. (Phase 5 changed this from 200 yr.)
4. Pick **Proxima**: its main sequence reads `1 s = 34.2 Gyr`.

## Tests
`pytest tests/ -q` gives **196 passed** (177 before this phase, plus 19 new):
- duration formatting, with negative input rejected;
- for all six presets, the stage clock matches `phase_schedule` mid-phase (elapsed time, duration, rate);
- the clock stops at the remnant;
- the Sun's main sequence runs at exactly 10 Gyr / 20 s;
- a red dwarf's compression spans more than 10⁶ (10⁸ before Phase 5; 4 × 10⁶ since Phase 7).
