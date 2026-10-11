# Realism upgrade: progress

Each phase lives on its own branch (`realism/phase-N-<name>`) and ends with a note in this folder.
The cited equations behind every phase are in [`equations/`](equations/README.md).

| Phase | Branch | Status | Note |
|---|---|---|---|
| Research | `realism/phase-0-audit` | ✅ Complete | [equations/](equations/README.md) |
| 0: Audit and baseline | `realism/phase-0-audit` | ✅ Complete | [00-audit.md](00-audit.md) |
| 1: Radiometry and colour | `realism/phase-1-radiometry` | ✅ Complete (visual check partial, see below) | [01-radiometry.md](01-radiometry.md) |
| 2: Starfield (HYG v4.2, CC BY-SA accepted) | — | ⏳ Next | — |
| 3: Stellar surface | — | Planned | — |
| 6: Time honesty | — | Planned | — |
| 5: Death scenes | — | Planned | — |
| 4: Black hole | — | Planned | — |
| 7: MIST tracks (optional) | — | Planned | — |

The order 1 → 2 → 3 → 6 → 5 → 4 → (7) is deliberate: the death scenes need the supernova day clock from Phase 6.

## Open items carried forward
- **Phase 1 visual check:** physical/fixed is captured for Proxima and the Sun only. Still to do:
  - physical/fixed for Sirius, Betelgeuse, Rigel and Eta Carinae;
  - physical/auto for all six presets;
  - a stylized "unchanged" check.

  Both earlier attempts stopped on low memory: Claude Code halted the headless runs. Plan: run the checks in a real Chrome window through the Claude-in-Chrome extension once it is connected.
- **Baseline screenshots** (`tests/visual/baseline/`, 11 MB) are kept local and gitignored. Regenerate them with `tests/visual/capture_baseline.py`.
- **Issue #14 is broader than filed:** any file change in the repo while `reflex run` is active can kill the backend (npm `EBUSY` on OneDrive). See 00-audit.md §5.
