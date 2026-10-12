"""Python wrapper for the local Three.js star scene.

Client-only (WebGL touches `window`), so this must be an rx.NoSSRComponent.
Python is authoritative for *what is physically true* (radius, color, stage,
how far through the stage it is) and pushes it as props; the JS side
(star_scene.jsx) owns *how it looks moving* -- the star's surface shader,
bloom, and the per-stage effects (supernova blast, planetary-nebula shell,
pulsar beams, black-hole lensing).

Implemented with vanilla Three.js rather than @react-three/fiber: fiber's
custom React renderer needs react-reconciler to reach into React's private
shared-internals object, and react-reconciler@0.33 (bundled by fiber@9)
crashes against React 19.2.x's renamed internals fields. Plain Three.js has
no dependency on React internals, so it avoids that whole compatibility gap.
"""

import reflex as rx

_scene_path = rx.asset("star_scene.jsx")


class StarScene(rx.NoSSRComponent):
    library = f"$/public{_scene_path}"
    tag = "StarScene"

    lib_dependencies: list[str] = [
        "three@0.185.1",
    ]

    radius: rx.Var[float]
    color: rx.Var[str]
    stage: rx.Var[str]
    luminosity: rx.Var[float]
    progress: rx.Var[float]
    # Optional (realism Phase 1). Without them the scene keeps the stylized look.
    surface_color: rx.Var[list[float]]
    surface_luminance: rx.Var[float]
    render_mode: rx.Var[str]
    exposure_mode: rx.Var[str]
    # Optional (realism Phase 3): surface physics for physical mode.
    limb_darkening: rx.Var[list[float]]
    granulation_cells: rx.Var[float]
    granulation_amplitude: rx.Var[float]
    temperature_sensitivity: rx.Var[list[float]]
    spot_contrast: rx.Var[list[float]]
    pulsation_period_days: rx.Var[float]
    glare: rx.Var[bool]
    coronagraph: rx.Var[bool]
    convection: rx.Var[float]
    # Optional (realism Phase 5): death scenes.
    nebula_color: rx.Var[list[float]]
    illustrative_effects: rx.Var[bool]


star_scene = StarScene.create
