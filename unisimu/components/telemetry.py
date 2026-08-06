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


def _stage_label() -> rx.Component:
    return rx.match(
        SimState.stage,
        *[(key, label) for key, label in STAGE_LABELS.items()],
        SimState.stage,
    )


def status_bar() -> rx.Component:
    return rx.hstack(
        rx.badge(
            rx.cond(SimState.playing, "● Playing", "⏸ Paused"),
            color_scheme=rx.cond(SimState.playing, "green", "gray"),
            size="2",
        ),
        rx.badge(_stage_label(), variant="soft", size="2"),
        rx.spacer(),
        rx.text("Age: ", rx.el.b(SimState.age_display), size="2"),
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
            rx.text(SimState.radius_display, " R☉", size="2"),
            width="100%",
        ),
        rx.progress(value=SimState.stage_progress_pct, width="100%"),
        spacing="2",
        align="start",
        width="100%",
    )
