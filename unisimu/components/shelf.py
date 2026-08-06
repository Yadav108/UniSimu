"""Browsable grid of preset stars -- the app's entry point. Clicking a card
jumps into the existing single-star detail view (SimState.select_preset)
already pre-loaded with that star's mass.

Observatory-logbook styling: rectangular hairline-bordered cards on a warm
near-black ground, a book-serif star name, and a monospace instrument-readout
line for spectral class + mass -- ported from the approved theme-study
mockup. Colors reference the custom properties in assets/theme.css rather
than generic Radix gray/accent tokens, so the shelf actually carries the
palette that was designed for it instead of the app's default dark theme.

PRESETS is static Python data, so this grid is built with a plain `for`
loop at compile time rather than `rx.foreach`."""

import reflex as rx

from unisimu.copy import FATE_ACCENT_HEX, STAGE_LABELS
from unisimu.physics.blackbody import kelvin_to_hex
from unisimu.physics.stellar import main_sequence_temperature_k
from unisimu.presets import PRESETS
from unisimu.state import SimState

_SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif"
_MONO = "'SF Mono', Consolas, Menlo, monospace"


def _preset_card(preset) -> rx.Component:
    swatch_color = kelvin_to_hex(main_sequence_temperature_k(preset.mass_msun))
    fate_label = STAGE_LABELS[preset.fate_stage]
    fate_hex = FATE_ACCENT_HEX[preset.fate_stage]
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    width="2.75em",
                    height="2.75em",
                    border_radius="50%",
                    background_color=swatch_color,
                    box_shadow=f"0 0 1.1em 0.05em {swatch_color}",
                    flex_shrink="0",
                ),
                rx.vstack(
                    rx.text(
                        preset.spectral_class,
                        size="2",
                        weight="bold",
                        color="var(--uni-brass)",
                        font_family=_MONO,
                    ),
                    rx.text(
                        f"{preset.mass_msun:g} M☉",
                        size="1",
                        color="var(--uni-ink-muted)",
                        font_family=_MONO,
                    ),
                    spacing="0",
                    align="end",
                ),
                justify="between",
                width="100%",
                align="start",
            ),
            rx.heading(
                preset.name,
                size="5",
                font_family=_SERIF,
                weight="regular",
                color="var(--uni-parchment)",
            ),
            rx.text(preset.blurb, size="2", color="var(--uni-ink-muted)"),
            rx.spacer(),
            rx.hstack(
                rx.text(
                    "Eventual fate",
                    size="1",
                    color="var(--uni-ink-muted)",
                    text_transform="uppercase",
                    letter_spacing="0.08em",
                ),
                rx.spacer(),
                rx.box(
                    fate_label,
                    font_size="0.6875em",
                    letter_spacing="0.08em",
                    text_transform="uppercase",
                    padding="0.3em 0.65em",
                    border=f"1px solid {fate_hex}",
                    color=fate_hex,
                ),
                width="100%",
                align="center",
                border_top="1px solid var(--uni-hairline)",
                padding_top="0.75em",
            ),
            spacing="3",
            align="start",
            height="100%",
        ),
        on_click=SimState.select_preset(preset.mass_msun),
        padding="1.25em",
        background_color="var(--uni-panel)",
        border="1px solid var(--uni-hairline)",
        cursor="pointer",
        min_width="0",
        overflow="hidden",
        _hover={
            "border_color": "var(--uni-brass-dim)",
            "transform": "translateY(-2px)",
            "box_shadow": f"0 0 1.75em -0.5em {swatch_color}",
        },
        transition="border-color 0.15s, transform 0.15s, box-shadow 0.15s",
    )


def shelf_page() -> rx.Component:
    return rx.box(
        rx.container(
            rx.vstack(
                rx.box(
                    rx.heading(
                        "Uni",
                        rx.el.em("Simu", color="var(--uni-brass-bright)", font_style="italic"),
                        size="8",
                        font_family=_SERIF,
                        weight="regular",
                        color="var(--uni-parchment)",
                    ),
                    rx.text(
                        "Pick a star to watch its life unfold, from formation to its "
                        "final fate.",
                        size="3",
                        color="var(--uni-ink-muted)",
                        text_transform="uppercase",
                        letter_spacing="0.06em",
                    ),
                    border_bottom="1px solid var(--uni-hairline)",
                    padding_bottom="1.5em",
                    width="100%",
                ),
                rx.box(
                    *[_preset_card(preset) for preset in PRESETS],
                    display="grid",
                    grid_template_columns="repeat(auto-fill, minmax(240px, 1fr))",
                    gap="1.25em",
                    width="100%",
                    min_width="0",
                    padding_top="1em",
                ),
                spacing="3",
                align="start",
                width="100%",
                min_width="0",
            ),
            padding="3em 1.5em 5em",
            size="4",
            width="100%",
        ),
        background_color="var(--uni-ground)",
        min_height="100vh",
        width="100%",
    )
