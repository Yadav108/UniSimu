# Realism upgrade: progress

Each phase lives on its own branch (`realism/phase-N-<name>`) and ends with a note in this folder.
The cited equations behind every phase are in [`equations/`](equations/README.md).

| Phase | Branch | Status | Note |
|---|---|---|---|
| Research | `realism/phase-0-audit` | ✅ Complete | [equations/](equations/README.md) |
| 0: Audit and baseline | `realism/phase-0-audit` | ✅ Complete | [00-audit.md](00-audit.md) |
| 1: Radiometry and colour | `realism/phase-1-radiometry` | ✅ Complete (visual check partial, see below) | [01-radiometry.md](01-radiometry.md) |
| 2: Starfield (HYG v4.2, CC BY-SA 4.0) | `realism/phase-2-starfield` | ✅ Complete (browser check pending) | [02-starfield.md](02-starfield.md) |
| 3: Stellar surface | `realism/phase-3-surface` | ✅ Complete (browser check pending) | [03-surface.md](03-surface.md) |
| 6: Time honesty | `realism/phase-6-time` | ✅ Complete (browser check pending) | [06-time.md](06-time.md) |
| 5: Death scenes | `realism/phase-5-death-scenes` | ✅ Complete (browser check pending) | [05-death-scenes.md](05-death-scenes.md) |
| 4: Black hole | — | ⏳ Next | — |
| 7: MIST tracks (optional) | — | Planned | — |

The order 1 → 2 → 3 → 6 → 5 → 4 → (7) is deliberate: the death scenes need the supernova day clock from Phase 6.

## Open items carried forward
- **Phase 5 browser check:** the supernova plateau reads `1 s = 40 d`, the green-cyan planetary nebula, the true-scale neutron star, and the Illustrative-effects switch (05-death-scenes.md).
- **Phase 6 browser check:** the Time rows read `1 s = 500 Myr` on the Sun's main sequence and `1 s = 2.1 kyr` at its planetary nebula (06-time.md).
- **Phase 3 browser check:** the hand checklist in 03-surface.md (limb darkening, granule sizes, coronagraph, glare, pulsation readout).
- **Phase 2 browser check:** steady (non-twinkling) catalogue stars, Orion and Sirius in the right places, a visible glow band, and the credit in Legend & Help. Use the hand checklist in 02-starfield.md.
- **Phase 1 visual check:** physical/fixed is captured for Proxima and the Sun only. Still to do:
  - physical/fixed for Sirius, Betelgeuse, Rigel and Eta Carinae;
  - physical/auto for all six presets;
  - a stylized "unchanged" check.

  Both earlier attempts stopped on low memory: Claude Code halted the headless runs. Plan: run the checks in a real Chrome window through the Claude-in-Chrome extension once it is connected.
- **Baseline screenshots** (`tests/visual/baseline/`, 11 MB) are kept local and gitignored. Regenerate them with `tests/visual/capture_baseline.py`.
- **Issue #14 is broader than filed:** any file change in the repo while `reflex run` is active can kill the backend (npm `EBUSY` on OneDrive). See 00-audit.md §5.
