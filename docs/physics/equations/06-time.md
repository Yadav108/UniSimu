# 06 — Time: cinematic clock vs true time

Used by: Phase 6 (and every animated effect).

## What the code does today (read from `unisimu/physics/stellar.py`)
`phase_schedule(mass)` returns four `(age_start, age_end, screen_seconds)` segments:

| Segment | Screen seconds at 1× |
|---|---|
| Protostar | 6 |
| Main sequence | 20 |
| Post-main-sequence | 14 |
| Terminal flash | 10 |

`cinematic_age_years(mass, screen_seconds)` maps screen time to true age, **piecewise-linearly within each segment**.
The rate in years per screen second is therefore

$$\dot a_i=\frac{a_{i,\rm end}-a_{i,\rm start}}{s_i}$$

which differs by many orders of magnitude between segments. For example, the Sun's MS segment runs at about 5 × 10⁸ yr/s, and the terminal flash (2000 yr over 10 s) at 200 yr/s.

## Rules for Phase 6
1. **Readout:** show the true simulated age, plus the current rate ȧ_i in yr/s (or d/s inside the supernova).
   - Add both as new `SimState` vars; the change is additive and existing payload keys are unchanged.
   - Use the same formatting helpers as `age_display`.
2. **Animation clocks:** spot drift, disc orbits, nebula expansion and pulsation are driven by wall-clock time in the JS.
   - Physical mode must say so with a label such as "motion not to scale".
   - Where a physical period P exists (docs 03 and 04), display it next to the label instead of implying it.
3. **Optional "true rate" mode** (decision D5, default off): for a process with period P, map wall time with a chosen constant factor and show that factor on screen.
4. **Supernova sub-clock:** Phase 5's `supernova_state(t_days, …)` gets t_days by mapping the terminal-flash segment linearly onto, e.g., 0–400 d. This replaces the generic `stage_progress` fractions, and the mapping constant is displayed.

No literature citation is needed: this is bookkeeping for the existing model.
