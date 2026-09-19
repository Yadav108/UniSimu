"""Life-stage progress strip: mirrors the textbook stellar-evolution
diagrams a user may already know (#2 match between system and real world),
and keeps the overall journey visible at a glance (#1 visibility of
system status).

Styled as the shelf's hairline "stamps": the current stage is filled brass,
stages already passed are brass outlines, and upcoming ones are dim."""

import reflex as rx

from unisimu.state import SimState
from unisimu.theme import MONO, STAMP

_STAGE_SHORT_LABELS = {
    "protostar": "Protostar",
    "main_sequence": "Main Seq.",
    "red_giant": "Red Giant",
    "red_supergiant": "Red Supergiant",
    "supernova": "Supernova",
    "planetary_nebula": "Nebula",
    "white_dwarf": "White Dwarf",
    "neutron_star": "Neutron Star",
    "black_hole": "Black Hole",
}


def _stage_chip(stage_var: rx.Var[str], index: rx.Var[int]) -> rx.Component:
    is_current = SimState.current_stage_index == index
    is_past = SimState.current_stage_index > index
    return rx.box(
        rx.match(
            stage_var,
            *[(key, label) for key, label in _STAGE_SHORT_LABELS.items()],
            stage_var,
        ),
        **STAMP,
        font_family=MONO,
        border=rx.cond(
            is_current,
            "1px solid var(--uni-brass)",
            rx.cond(is_past, "1px solid var(--uni-brass-dim)", "1px solid var(--uni-hairline)"),
        ),
        background_color=rx.cond(is_current, "var(--uni-brass)", "transparent"),
        color=rx.cond(
            is_current,
            "var(--uni-ground)",
            rx.cond(is_past, "var(--uni-brass)", "var(--uni-ink-muted)"),
        ),
        font_weight=rx.cond(is_current, "700", "400"),
        transition="background-color 0.3s, color 0.3s, border-color 0.3s",
    )


def timeline() -> rx.Component:
    return rx.hstack(
        rx.foreach(
            SimState.stage_track_list,
            lambda stage, i: rx.fragment(
                rx.cond(i > 0, rx.text("→", color="var(--uni-brass-dim)"), rx.fragment()),
                _stage_chip(stage, i),
            ),
        ),
        spacing="2",
        align="center",
        wrap="wrap",
    )
