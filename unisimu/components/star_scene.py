"""Python wrapper for the local Three.js star scene.

Client-only (WebGL touches `window`), so this must be an rx.NoSSRComponent.
Python is authoritative for *what is physically true* (radius, color, ...)
and pushes it as props; the JS side (star_scene.jsx) owns *how it looks
moving* -- interpolation, rotation, and later, event-triggered animation.

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


star_scene = StarScene.create
