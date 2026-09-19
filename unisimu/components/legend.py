"""Help/legend popover: color-temperature key, terminal-stage meanings,
mass thresholds, and keyboard shortcuts, looked up in place rather than
memorized (#6 recognition rather than recall, #10 help and documentation)."""

import reflex as rx

_COLOR_TEMP_ROWS = [
    ("#9bb0ff", "Hot (O/B-type, >10,000 K)"),
    ("#ffffff", "Sun-like (G-type, ~5,800 K)"),
    ("#ffcc6f", "Cool (K-type, ~4,000 K)"),
    ("#ff6a3d", "Cold (M-type / protostar, <3,000 K)"),
]

_TERMINAL_ROWS = [
    ("White Dwarf", "Low/mid-mass stars (<8 M☉) shed their outer layers and cool as dense embers."),
    ("Neutron Star", "8-20 M☉ stars end in a supernova, collapsing to an ultra-dense core."),
    ("Black Hole", "Stars ≥20 M☉ collapse past the neutron-degeneracy limit after their supernova."),
]

_SHORTCUT_ROWS = [
    ("Space", "Play / Pause"),
    ("R", "Reset"),
]


def _color_legend() -> rx.Component:
    return rx.vstack(
        rx.heading("Star color ↔ temperature", size="2"),
        *[
            rx.hstack(
                rx.box(width="1em", height="1em", border_radius="50%", background_color=color),
                rx.text(desc, size="2"),
                spacing="2",
                align="center",
            )
            for color, desc in _COLOR_TEMP_ROWS
        ],
        spacing="1",
        align="start",
    )


def _terminal_legend() -> rx.Component:
    return rx.vstack(
        rx.heading("How a star's life ends", size="2"),
        *[
            rx.vstack(
                rx.text(name, weight="medium", size="2"),
                rx.text(desc, size="2", color_scheme="gray"),
                spacing="0",
                align="start",
            )
            for name, desc in _TERMINAL_ROWS
        ],
        spacing="2",
        align="start",
    )


def _shortcuts_legend() -> rx.Component:
    return rx.vstack(
        rx.heading("Keyboard shortcuts", size="2"),
        *[
            rx.hstack(
                rx.code(key, size="2"),
                rx.text(desc, size="2", color_scheme="gray"),
                spacing="2",
            )
            for key, desc in _SHORTCUT_ROWS
        ],
        spacing="1",
        align="start",
    )


def legend() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(rx.button("Legend & Help", variant="soft", size="2")),
        rx.popover.content(
            rx.vstack(
                _color_legend(),
                rx.separator(size="4"),
                _terminal_legend(),
                rx.separator(size="4"),
                _shortcuts_legend(),
                spacing="4",
                align="start",
            ),
            max_width="24em",
            class_name="uni-detail",
        ),
    )
