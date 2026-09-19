"""Top-level page: routes between the preset shelf (entry point) and the
single-star detail view, via SimState.view. Detail layout is status bar +
timeline up top, the 3D viewport as the dominant element, and
controls/telemetry/legend in a sidebar. See each component module for the
specific Nielsen-heuristic mapping.

Layout: on md+ the page is exactly one screen tall, the viewport fills the
row beside a fixed-width sidebar, and the sidebar scrolls on its own if it's
taller than the screen. Below md everything stacks and the page itself scrolls
-- nothing is clipped at any size."""

import reflex as rx

from unisimu.components.controls import controls
from unisimu.components.hr_diagram import hr_diagram
from unisimu.components.legend import legend
from unisimu.components.shelf import shelf_page
from unisimu.components.telemetry import status_bar, telemetry_readout
from unisimu.components.timeline import timeline
from unisimu.components.viewport import viewport
from unisimu.state import SimState
from unisimu.theme import SERIF


def _header() -> rx.Component:
    return rx.hstack(
        rx.button(
            "← Shelf",
            on_click=SimState.back_to_shelf,
            variant="outline",
            size="2",
        ),
        rx.heading(
            "Uni",
            rx.el.em("Simu", color="var(--uni-brass-bright)", font_style="italic"),
            size="6",
            font_family=SERIF,
            weight="regular",
            color="var(--uni-parchment)",
        ),
        width="100%",
        align="center",
        spacing="4",
    )


def _sidebar() -> rx.Component:
    return rx.vstack(
        controls(),
        rx.separator(size="4"),
        telemetry_readout(),
        rx.separator(size="4"),
        hr_diagram(),
        rx.separator(size="4"),
        legend(),
        spacing="4",
        align="start",
        width=rx.breakpoints(initial="100%", md="22em"),
        flex_shrink="0",
        box_sizing="border-box",
        padding="1.25em",
        background_color="var(--uni-panel)",
        border="1px solid var(--uni-hairline)",
        min_height="0",
        overflow_y=rx.breakpoints(initial="visible", md="auto"),
    )


def detail_page() -> rx.Component:
    return rx.box(
        rx.vstack(
            _header(),
            status_bar(),
            timeline(),
            rx.flex(
                viewport(),
                _sidebar(),
                direction=rx.breakpoints(initial="column", md="row"),
                spacing="4",
                width="100%",
                flex="1",
                min_height="0",
            ),
            spacing="4",
            width="100%",
            height="100%",
        ),
        # scopes the serif heading style in assets/theme.css to this page
        class_name="uni-detail",
        padding="1em",
        width="100%",
        box_sizing="border-box",
        min_height="100vh",
        height=rx.breakpoints(initial="auto", md="100vh"),
        background_color="var(--uni-ground)",
        overflow_x="hidden",
    )


def index() -> rx.Component:
    return rx.fragment(
        rx.window_event_listener(on_key_down=SimState.handle_key),
        rx.cond(SimState.view == "shelf", shelf_page(), detail_page()),
    )
