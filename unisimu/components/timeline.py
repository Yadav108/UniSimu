"""Life-stage progress strip: mirrors the textbook stellar-evolution
diagrams a user may already know (#2 match between system and real world),
and keeps the overall journey visible at a glance (#1 visibility of
system status)."""

import reflex as rx

from unisimu.state import SimState

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
    return rx.badge(
        rx.match(
            stage_var,
            *[(key, label) for key, label in _STAGE_SHORT_LABELS.items()],
            stage_var,
        ),
        variant=rx.cond(is_current, "solid", rx.cond(is_past, "soft", "outline")),
        color_scheme=rx.cond(is_current, "violet", rx.cond(is_past, "gray", "gray")),
        size="2",
    )


def timeline() -> rx.Component:
    return rx.hstack(
        rx.foreach(
            SimState.stage_track_list,
            lambda stage, i: rx.fragment(
                rx.cond(i > 0, rx.text("→", color_scheme="gray"), rx.fragment()),
                _stage_chip(stage, i),
            ),
        ),
        spacing="2",
        align="center",
        wrap="wrap",
    )
