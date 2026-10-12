"""Optional reader for MIST stellar evolution tracks (realism Phase 7, decision D6).

MIST (Choi et al. 2016, https://mist.science) states "All rights reserved", so
no MIST data ships with UniSimu. If you download EEP track files yourself,
`tools/build_mist_tracks.py` turns them into a local, gitignored table that
this module reads. Nothing in the app depends on it; the analytic model in
stellar.py stays the default and the fallback.

EEP file layout, from MIST's own reader (read_mist_models.py, J. Choi): 11
header lines (initial mass is token 1 of line 7, counting from 0), then a
column-name line starting with '#', then whitespace-separated numbers. The
column names `log_Teff`, `log_L` and `phase` are confirmed by that reader;
`star_age` is the expected age column but was NOT confirmed there, so the
parser reports it clearly if absent.
"""

import json
import math
from bisect import bisect_right
from pathlib import Path

# FSPS phase codes, as documented in read_mist_models.py
MIST_PHASES = {-1: "PMS", 0: "MS", 2: "SGB+RGB", 3: "CHeB", 4: "EAGB", 5: "TPAGB", 6: "post-AGB", 9: "WR"}
DEFAULT_TABLE = Path(__file__).resolve().parents[2] / "data" / "mist_tracks.json"

SUN_TEMPERATURE_K = 5772.0  # IAU nominal; radius from Stefan-Boltzmann in solar units


def parse_eep(text: str) -> dict:
    """Parse one MIST .eep file: initial mass and the age/T/L/phase columns."""
    lines = text.splitlines()
    minit = float(lines[7].split()[1])
    names = lines[11].lstrip("#").split()
    needed = ("star_age", "log_Teff", "log_L", "phase")
    missing = [n for n in needed if n not in names]
    if missing:
        raise ValueError(f"EEP file lacks column(s) {missing}; found {names[:12]}...")
    idx = {n: names.index(n) for n in needed}
    rows = [line.split() for line in lines[12:] if line.strip() and not line.lstrip().startswith("#")]
    return {
        "initial_mass": minit,
        "age_years": [float(r[idx["star_age"]]) for r in rows],
        "log_teff": [float(r[idx["log_Teff"]]) for r in rows],
        "log_l": [float(r[idx["log_L"]]) for r in rows],
        "phase": [int(round(float(r[idx["phase"]]))) for r in rows],
    }


def stage_for_phase(phase: int, initial_mass: float) -> str | None:
    """Map a MIST phase code onto a UniSimu stage name (None: no equivalent)."""
    if phase == -1:
        return "protostar"
    if phase == 0:
        return "main_sequence"
    if phase in (2, 3, 4, 5):
        return "red_supergiant" if initial_mass >= 8.0 else "red_giant"
    if phase == 6:
        return "planetary_nebula"
    return None  # WR (9) and anything undocumented


def state_at(track: dict, age_years: float) -> dict:
    """Linearly interpolated (in age) temperature, luminosity, radius and stage."""
    ages = track["age_years"]
    i = min(max(bisect_right(ages, age_years) - 1, 0), len(ages) - 2)
    f = min(max((age_years - ages[i]) / (ages[i + 1] - ages[i]), 0.0), 1.0)
    log_t = track["log_teff"][i] + f * (track["log_teff"][i + 1] - track["log_teff"][i])
    log_l = track["log_l"][i] + f * (track["log_l"][i + 1] - track["log_l"][i])
    temperature, luminosity = 10**log_t, 10**log_l
    radius = math.sqrt(luminosity) * (SUN_TEMPERATURE_K / temperature) ** 2
    phase = track["phase"][i if f < 0.5 else i + 1]
    return {
        "temperature_k": temperature,
        "luminosity_lsun": luminosity,
        "radius_rsun": radius,
        "stage": stage_for_phase(phase, track["initial_mass"]),
    }


def load_tracks(path: Path = DEFAULT_TABLE) -> list[dict] | None:
    """The locally built table, or None if the user hasn't built one."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))["tracks"]
