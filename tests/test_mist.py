"""Tests for the optional MIST reader (realism Phase 7). No MIST data ships with
the repo, so these use a synthetic file in the documented layout; the
comparison with the analytic model runs only if you built data/mist_tracks.json."""

import pytest

from unisimu.physics import mist, stellar

HEADER = [
    "# MIST version number  = 1.2",
    "# MESA revision number = 7503",
    "# --------------------------------------------------------------------------------------",
    "#  Yinit        Zinit   [Fe/H]   [a/Fe]  v/vcrit",
    "#  0.2703  1.42857E-02     0.00     0.00     0.40",
    "# --------------------------------------------------------------------------------------",
    "#  initial_mass   N_pts   N_EEP   N_col   phase        type",
    "#    1.0000000E+00     4       9      5     YES    low-mass",
    "# --------------------------------------------------------------------------------------",
    "#  EEPs:      1",
    "# --------------------------------------------------------------------------------------",
    "#   star_age   log_Teff   log_L   log_g   phase",
]
ROWS = [
    "1.0E+05  3.60  0.50  3.0  -1",
    "1.0E+08  3.76  0.00  4.4  0",
    "1.0E+10  3.70  0.50  3.8  2",
    "1.2E+10  3.55  3.00  0.5  5",
]
SYNTHETIC = "\n".join(HEADER + ROWS) + "\n"


def test_parse_reads_mass_and_columns():
    track = mist.parse_eep(SYNTHETIC)
    assert track["initial_mass"] == 1.0
    assert track["age_years"] == [1e5, 1e8, 1e10, 1.2e10]
    assert track["phase"] == [-1, 0, 2, 5]


def test_parse_reports_a_missing_age_column_clearly():
    broken = SYNTHETIC.replace("star_age", "age_star")
    with pytest.raises(ValueError, match="star_age"):
        mist.parse_eep(broken)


def test_phase_mapping():
    assert mist.stage_for_phase(-1, 1.0) == "protostar"
    assert mist.stage_for_phase(0, 1.0) == "main_sequence"
    assert mist.stage_for_phase(2, 1.0) == "red_giant"
    assert mist.stage_for_phase(3, 16.5) == "red_supergiant"
    assert mist.stage_for_phase(6, 1.0) == "planetary_nebula"
    assert mist.stage_for_phase(9, 40.0) is None


def test_state_interpolates_in_age_and_uses_stefan_boltzmann():
    track = mist.parse_eep(SYNTHETIC)
    s = mist.state_at(track, 1e8)
    assert s["stage"] == "main_sequence"
    assert s["temperature_k"] == pytest.approx(10**3.76)
    # mist.py uses the IAU 5772 K for T_sun, stellar.py 5778 K: a 0.2 % radius difference
    assert s["radius_rsun"] == pytest.approx(stellar.radius_from_luminosity_temperature(1.0, 10**3.76), rel=3e-3)


def test_no_table_means_no_mist(tmp_path):
    assert mist.load_tracks(tmp_path / "absent.json") is None


@pytest.mark.skipif(mist.load_tracks() is None, reason="no local MIST table (data/mist_tracks.json)")
def test_mist_and_analytic_agree_on_broad_stage_order():
    order = ["protostar", "main_sequence", "red_giant", "red_supergiant", "planetary_nebula"]
    for track in mist.load_tracks():
        stages = [mist.stage_for_phase(p, track["initial_mass"]) for p in track["phase"]]
        seen = [s for i, s in enumerate(stages) if s and (i == 0 or stages[i - 1] != s)]
        analytic = [s for s in stellar.stage_track(track["initial_mass"]) if s in order]
        assert [s for s in seen if s in analytic] == [s for s in analytic if s in seen]
