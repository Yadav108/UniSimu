"""Full-bleed 3D viewport: the dominant visual element with minimal
overlapping chrome (#8 aesthetic and minimalist design)."""

import reflex as rx

from unisimu.components.star_scene import star_scene
from unisimu.state import SimState


def viewport() -> rx.Component:
    return rx.box(
        star_scene(
            radius=SimState.radius_rsun,
            color=SimState.color_hex,
            stage=SimState.stage,
            luminosity=SimState.luminosity_lsun,
            progress=SimState.stage_progress,
        ),
        width="100%",
        height="100%",
        min_height="50vh",
        # Matches the scene's own clear color (star_scene.jsx SPACE_COLOR) so
        # the canvas edge is invisible before/while WebGL initialises.
        background_color="#03040a",
        border="1px solid var(--uni-hairline)",
        border_radius="var(--radius-4)",
        overflow="hidden",
    )
