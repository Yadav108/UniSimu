"""Top-level page: routes between the preset shelf (entry point) and the
single-star detail view, via SimState.view. Detail layout is status bar +
timeline up top, full-bleed 3D viewport as the dominant element,
controls/telemetry/legend in a sidebar. See each component module for the
specific Nielsen-heuristic mapping."""

import reflex as rx

from unisimu.components.controls import controls
from unisimu.components.legend import legend
from unisimu.components.shelf import shelf_page
from unisimu.components.telemetry import status_bar, telemetry_readout
from unisimu.components.timeline import timeline
from unisimu.components.viewport import viewport
from unisimu.state import SimState


def detail_page() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.button(
                    "← Shelf",
                    on_click=SimState.back_to_shelf,
                    variant="soft",
                    size="2",
                ),
                rx.heading("UniSimu", size="6"),
                rx.spacer(),
                rx.color_mode.button(),
                width="100%",
                align="center",
            ),
            status_bar(),
            timeline(),
            rx.separator(size="4"),
            rx.flex(
                viewport(),
                rx.vstack(
                    controls(),
                    rx.separator(size="4"),
                    telemetry_readout(),
                    rx.separator(size="4"),
                    legend(),
                    spacing="4",
                    align="start",
                    width=rx.breakpoints(initial="100%", md="20em"),
                    flex_shrink="0",
                ),
                direction=rx.breakpoints(initial="column", md="row"),
                spacing="4",
                width="100%",
                flex="1",
            ),
            spacing="4",
            width="100%",
            height="100%",
        ),
        padding="1em",
        width="100vw",
        height="100vh",
        box_sizing="border-box",
    )


def index() -> rx.Component:
    return rx.fragment(
        rx.window_event_listener(on_key_down=SimState.handle_key),
        rx.toast.provider(),
        rx.cond(SimState.view == "shelf", shelf_page(), detail_page()),
    )
