"""Mass slider, transport controls (play/pause/reset), and speed selector.

Nielsen mapping:
  - Play/Pause/Reset as three distinct always-present buttons, not one
    overloaded toggle (#3 user control and freedom).
  - Mass slider hard-clamped to a valid range, with inline microcopy
    explaining that changing it mid-run restarts the star (#5 error
    prevention, #9 recognize/diagnose/recover from errors).
  - Speed as a segmented control of discrete, visible choices rather than
    free text (#6 recognition over recall).
  - Play is disabled with an explanatory tooltip once a star reaches its
    terminal stage, instead of a dead click (#5, #9).
"""

import reflex as rx

from unisimu.state import MAX_MASS_MSUN, MIN_MASS_MSUN, SPEED_OPTIONS, SimState


def _transport_buttons() -> rx.Component:
    play_button = rx.button(
        "Play",
        on_click=SimState.play,
        disabled=SimState.playing | SimState.is_terminal,
        variant="solid",
    )
    return rx.hstack(
        rx.cond(
            SimState.is_terminal,
            rx.tooltip(
                play_button,
                content="This star has ended its life. Press Reset to simulate a new one.",
            ),
            play_button,
        ),
        rx.button("Pause", on_click=SimState.pause, disabled=~SimState.playing, variant="soft"),
        rx.button("Reset", on_click=SimState.reset_simulation, variant="outline"),
        spacing="3",
    )


def _mass_control() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Initial mass", weight="medium", size="2"),
            rx.spacer(),
            rx.text(SimState.mass_display, " M☉", size="2", color_scheme="gray"),
            width="100%",
        ),
        rx.slider(
            min=MIN_MASS_MSUN,
            max=MAX_MASS_MSUN,
            step=0.1,
            default_value=[SimState.mass_msun],
            on_value_commit=SimState.set_mass,
            width="100%",
        ),
        rx.cond(
            SimState.playing,
            rx.text(
                "Changing mass restarts the star from formation.",
                size="1",
                color_scheme="gray",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="1",
        align="start",
    )


def _speed_control() -> rx.Component:
    return rx.vstack(
        rx.text("Playback speed", weight="medium", size="2"),
        rx.segmented_control.root(
            *[rx.segmented_control.item(f"{s}×", value=s) for s in SPEED_OPTIONS],
            value=SimState.speed_display,
            on_change=SimState.set_speed,
        ),
        spacing="1",
        align="start",
    )


def controls() -> rx.Component:
    return rx.vstack(
        _transport_buttons(),
        _mass_control(),
        _speed_control(),
        spacing="4",
        align="start",
        width="100%",
    )
