# UniSimu

An interactive single-star stellar evolution simulator, built with [Reflex](https://reflex.dev)
(Python, compiling to a React/Vite frontend) and a vanilla Three.js 3D viewport.

Pick a star — or dial in your own mass — and watch it live out its entire life, from
protostar to main sequence to its final fate as a white dwarf, neutron star, or black
hole, compressed into a few minutes of simulated time.

## Features

- **Preset shelf** — browse six real, recognizable stars (Proxima Centauri, the Sun,
  Sirius A, Betelgeuse, Rigel, Eta Carinae) spanning all three terminal fates, or dial in
  any mass from 0.1 to 150 solar masses.
- **3D star viewport** — a live Three.js scene with a glowing corona, starfield
  background, physically-motivated rotation speed per stage, an accretion disk for
  collapsed remnants, and camera auto-zoom that frames each stage as the star changes
  size.
- **Server-driven simulation** — a background tick loop advances simulated time (adjustable
  0.25x–16x) and streams the star's radius, temperature, luminosity, and color to the
  client every tick, derived from a deterministic mass-luminosity/lifetime model.
- **Stage-transition toasts** — a short explanation pops up each time the star crosses
  into a new life stage (e.g. "the core runs out of hydrogen...").
- **Timeline + telemetry** — a progress track showing the star's full stage sequence (which
  differs by mass) and a live instrument readout of its current physical properties.
- **Keyboard shortcuts** — `Space` to play/pause, `R` to reset.

## Tech stack

- **Backend/UI**: [Reflex](https://reflex.dev) 0.9 (Python), compiling to React 19 + Vite
- **3D rendering**: vanilla [Three.js](https://threejs.org) (no react-three-fiber — see
  [Notes](#notes) below)
- **Physics**: a small dependency-free simplified stellar-evolution model
  (`unisimu/physics/`)
- **Tests**: pytest

## Getting started

Requires Python 3.11+ and Node.js (Reflex uses it to run the compiled frontend).

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (compiles the frontend on first run)
reflex run
```

Then open **http://localhost:3000**.

## Running tests

```bash
pytest tests/ -q
```

Tests cover the blackbody color model, the stellar evolution stage/lifetime math, and
the preset shelf's mass-to-fate assignments.

## Project structure

```
unisimu/
  physics/
    blackbody.py       # temperature (K) -> RGB hex color
    stellar.py          # evolve(mass, age) -> StellarSnapshot; stage/lifetime model
  components/
    star_scene.py        # Python wrapper around the JS Three.js component
    viewport.py           # 3D viewport layout
    shelf.py               # preset star browsing grid
    controls.py             # mass/speed/play controls
    timeline.py               # stage-track progress bar
    telemetry.py                # live readout of star properties
    legend.py                     # stage glossary
  pages/index.py          # routes between the shelf and the detail view
  presets.py                # named real-star presets (mass, blurb, spectral class)
  copy.py                     # UI copy: stage labels, transition captions
  state.py                      # SimState: user controls + background simulation loop
assets/star_scene.jsx    # the Three.js scene (scene setup, glow, disk, camera zoom)
tests/                     # pytest suite for the physics model and presets
```

## How the simulation works

`unisimu/physics/stellar.py` implements a simplified, deterministic stellar-evolution
model — not a research-grade stellar-structure integration, but enough to drive a
plausible, mass-dependent visualization using standard scaling relations:

- Mass-luminosity and main-sequence lifetime relations set how bright and how long-lived
  a star of a given mass is.
- Stars below 8 M☉ swell into a red giant, shed their outer layers as a planetary nebula,
  and settle into a white dwarf.
- Stars between 8–20 M☉ become red supergiants, go supernova, and collapse into a
  neutron star.
- Stars at or above 20 M☉ follow the same path but collapse into a black hole instead.

`SimState` (in `unisimu/state.py`) drives an async background loop that advances
simulated years each tick and pushes the resulting snapshot (stage, radius, temperature,
luminosity, color) to the frontend, which the Three.js scene animates toward smoothly.

## Notes

The 3D viewport is built with vanilla Three.js rather than `@react-three/fiber`/`drei`:
`react-reconciler@0.33` (bundled by fiber@9) is currently incompatible with React
19.2.x's renamed internals, so the scene is wired up directly against the Three.js API
instead.

## License

MIT — see [LICENSE](LICENSE).
