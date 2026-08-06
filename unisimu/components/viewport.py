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
        ),
        width="100%",
        height="100%",
        min_height="50vh",
        border_radius="var(--radius-4)",
        overflow="hidden",
    )
