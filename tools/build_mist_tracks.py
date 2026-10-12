"""Turn MIST .eep track files you downloaded into data/mist_tracks.json.

Offline, optional, and LOCAL ONLY: MIST data is "All rights reserved"
(https://mist.science), so the output is gitignored and must not be committed
(decision D6). Usage, from the repo root:

    python tools/build_mist_tracks.py path/to/folder/with/eep/files

Download EEP tracks from https://mist.science (e.g. the packaged grid for
[Fe/H] = 0, v/vcrit = 0.4) and point this at the folder of *.track.eep files.
Cite Choi et al. 2016 (ApJ 823, 102) and Dotter 2016 if you use them.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unisimu.physics.mist import DEFAULT_TABLE, parse_eep  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    files = sorted(Path(sys.argv[1]).glob("*.eep"))
    if not files:
        sys.exit(f"no .eep files in {sys.argv[1]}")
    tracks = [parse_eep(f.read_text(encoding="utf-8")) for f in files]
    tracks.sort(key=lambda t: t["initial_mass"])
    DEFAULT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_TABLE.write_text(json.dumps({"source": "MIST (Choi et al. 2016), local only", "tracks": tracks}),
                             encoding="utf-8")
    masses = ", ".join(f"{t['initial_mass']:g}" for t in tracks)
    print(f"wrote {DEFAULT_TABLE} with {len(tracks)} tracks: {masses} M_sun")


if __name__ == "__main__":
    main()
