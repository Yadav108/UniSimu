"""The 3D viewport: the dominant visual element, with a single, quiet piece
of chrome over it -- the caption explaining each stage transition (#8
aesthetic and minimalist design)."""

import reflex as rx

from unisimu.components.star_scene import star_scene
from unisimu.state import SimState
from unisimu.theme import MONO, SERIF


def _caption_overlay() -> rx.Component:
    """Themed replacement for a toast: bottom-left of the scene, fades in,
    and (via CSS, see assets/theme.css) fades out on its own. Keyed on the
    text so each new caption restarts the animation."""
    return rx.cond(
        SimState.caption_text != "",
        rx.box(
            rx.text(
                SimState.caption_title,
                font_size="0.6875em",
                letter_spacing="0.1em",
                text_transform="uppercase",
                color="var(--uni-brass)",
                font_family=MONO,
            ),
            rx.text(
                SimState.caption_text,
                size="2",
                color="var(--uni-parchment)",
                font_family=SERIF,
                line_height="1.55",
            ),
            key=SimState.caption_text,
            class_name=rx.cond(
                SimState.caption_persistent, "uni-caption uni-caption--stay", "uni-caption"
            ),
            position="absolute",
            left="1em",
            right="1em",
            bottom="1em",
            max_width="34em",
            padding="0.8em 1em",
            background_color="rgba(20, 17, 13, 0.78)",
            backdrop_filter="blur(6px)",
            border="1px solid var(--uni-hairline)",
            border_left="2px solid var(--uni-brass)",
            # never intercept drags meant for the orbit controls underneath
            pointer_events="none",
        ),
    )


def viewport() -> rx.Component:
    return rx.box(
        star_scene(
            radius=SimState.radius_rsun,
            color=SimState.color_hex,
            stage=SimState.stage,
            luminosity=SimState.luminosity_lsun,
            progress=SimState.stage_progress,
        ),
        _caption_overlay(),
        position="relative",
        width="100%",
        min_width="0",
        # Stacked on small screens (fixed height, page scrolls); beside the
        # sidebar on md+, where the flex row stretches it to fill the height.
        height=rx.breakpoints(initial="60vh", md="auto"),
        min_height=rx.breakpoints(initial="20em", md="24em"),
        # Matches the scene's own clear color (star_scene.jsx SPACE_COLOR) so
        # the canvas edge is invisible before/while WebGL initialises.
        background_color="#03040a",
        border="1px solid var(--uni-hairline)",
        border_radius="var(--radius-4)",
        overflow="hidden",
    )
