"""Always-visible status bar and physical-property readout.

Nielsen mapping:
  - Playing/paused indicator + stage badge + sim-time always on screen
    (#1 visibility of system status).
  - Plain-language stage name, human-scaled age units, astronomer-standard
    units for T/L/R (#2 match between system and real world), showing only
    what matters rather than raw internal state (#8 minimalist design).
"""

import reflex as rx

from unisimu.copy import STAGE_LABELS
from unisimu.state import SimState
from unisimu.theme import MONO, STAMP


def _stage_label() -> rx.Component:
    return rx.match(
        SimState.stage,
        *[(key, label) for key, label in STAGE_LABELS.items()],
        SimState.stage,
    )


def _play_indicator() -> rx.Component:
    """A small brass lamp: lit and pulsing while the sim runs, dark when paused."""
    return rx.hstack(
        rx.box(
            width="0.55em",
            height="0.55em",
            border_radius="50%",
            flex_shrink="0",
            background_color=rx.cond(SimState.playing, "var(--uni-brass-bright)", "var(--uni-hairline)"),
            box_shadow=rx.cond(SimState.playing, "0 0 0.7em var(--uni-brass)", "none"),
            class_name=rx.cond(SimState.playing, "uni-pulse", ""),
        ),
        rx.text(
            rx.cond(SimState.playing, "Playing", "Paused"),
            font_family=MONO,
            font_size="0.75em",
            letter_spacing="0.08em",
            text_transform="uppercase",
            color=rx.cond(SimState.playing, "var(--uni-brass-bright)", "var(--uni-ink-muted)"),
        ),
        spacing="2",
        align="center",
    )


def status_bar() -> rx.Component:
    return rx.hstack(
        _play_indicator(),
        rx.box(
            _stage_label(),
            **STAMP,
            font_family=MONO,
            border="1px solid var(--uni-brass-dim)",
            color="var(--uni-brass)",
        ),
        rx.spacer(),
        rx.text(
            "Age ",
            rx.el.b(SimState.age_display),
            size="2",
            font_family=MONO,
            # digits change width every tick; keep the readout from wobbling
            font_variant_numeric="tabular-nums",
            color="var(--uni-parchment)",
        ),
        width="100%",
        align="center",
    )


def telemetry_readout() -> rx.Component:
    return rx.vstack(
        rx.heading("Star properties", size="3"),
        rx.hstack(
            rx.text("Temperature", size="2", color_scheme="gray"),
            rx.spacer(),
            rx.text(SimState.temperature_display, " K", size="2"),
            width="100%",
        ),
        rx.hstack(
            rx.text("Luminosity", size="2", color_scheme="gray"),
            rx.spacer(),
            rx.text(SimState.luminosity_display, " L☉", size="2"),
            width="100%",
        ),
        rx.hstack(
            rx.text("Radius", size="2", color_scheme="gray"),
            rx.spacer(),
            rx.text(SimState.radius_display, size="2"),
            width="100%",
        ),
        rx.progress(value=SimState.stage_progress_pct, width="100%"),
        spacing="2",
        align="start",
        width="100%",
    )
