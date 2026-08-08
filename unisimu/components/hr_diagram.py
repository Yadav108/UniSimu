"""H-R diagram panel: the star's evolutionary path in temperature-luminosity
space (log-log, temperature reversed hot-to-cool per astronomy convention),
with a live marker at its current position.

Nielsen mapping: #2 match between system and the real world -- this is the
standard astronomer's tool for reading a star's life stage at a glance,
alongside the plain-language telemetry readout it sits next to.
"""

import reflex as rx

from unisimu.hr_geometry import PLOT_BOTTOM, PLOT_LEFT, PLOT_RIGHT, PLOT_TOP, VIEW_HEIGHT, VIEW_WIDTH
from unisimu.state import SimState

_AXIS_LABEL_ATTRS = {"fill": "var(--uni-parchment)", "fontSize": "9", "textAnchor": "middle"}
_TICK_LABEL_ATTRS = {"fill": "var(--uni-ink-muted)", "fontSize": "8"}
_GRIDLINE_ATTRS = {"stroke": "var(--uni-hairline)", "strokeWidth": "1"}


def _t_gridlines() -> rx.Component:
    return rx.foreach(
        SimState.hr_t_ticks,
        lambda tick: rx.el.svg.g(
            rx.el.svg.line(
                x1=tick[0].to(str), x2=tick[0].to(str), y1=str(PLOT_TOP), y2=str(PLOT_BOTTOM),
                custom_attrs=_GRIDLINE_ATTRS,
            ),
            rx.el.svg.text(
                tick[1], x=tick[0].to(str), y=str(PLOT_BOTTOM + 14),
                custom_attrs={**_TICK_LABEL_ATTRS, "textAnchor": "middle"},
            ),
        ),
    )


def _l_gridlines() -> rx.Component:
    return rx.foreach(
        SimState.hr_l_ticks,
        lambda tick: rx.el.svg.g(
            rx.el.svg.line(
                x1=str(PLOT_LEFT), x2=str(PLOT_RIGHT), y1=tick[0].to(str), y2=tick[0].to(str),
                custom_attrs=_GRIDLINE_ATTRS,
            ),
            rx.el.svg.text(
                tick[1], x=str(PLOT_LEFT - 6), y=(tick[0] + 3).to(str),
                custom_attrs={**_TICK_LABEL_ATTRS, "textAnchor": "end"},
            ),
        ),
    )


def hr_diagram() -> rx.Component:
    return rx.vstack(
        rx.heading("H-R diagram", size="3"),
        rx.el.svg(
            rx.el.svg.rect(
                x=str(PLOT_LEFT), y=str(PLOT_TOP),
                width=str(PLOT_RIGHT - PLOT_LEFT), height=str(PLOT_BOTTOM - PLOT_TOP),
                custom_attrs={"fill": "var(--uni-panel-raised)"},
            ),
            _t_gridlines(),
            _l_gridlines(),
            rx.el.svg.polyline(
                points=SimState.hr_track_svg,
                custom_attrs={
                    "fill": "none",
                    "stroke": "var(--uni-brass-dim)",
                    "strokeWidth": "2",
                    "strokeLinecap": "round",
                    "strokeLinejoin": "round",
                },
            ),
            rx.el.svg.circle(
                cx=SimState.hr_marker_xy[0].to(str),
                cy=SimState.hr_marker_xy[1].to(str),
                r="5",
                custom_attrs={"fill": SimState.color_hex, "stroke": "var(--uni-panel)", "strokeWidth": "2"},
            ),
            rx.el.svg.text(
                "Temperature (K)", x=str((PLOT_LEFT + PLOT_RIGHT) / 2), y=str(VIEW_HEIGHT - 4),
                custom_attrs=_AXIS_LABEL_ATTRS,
            ),
            rx.el.svg.text(
                "Luminosity (L☉)", x="12", y=str((PLOT_TOP + PLOT_BOTTOM) / 2),
                custom_attrs={
                    **_AXIS_LABEL_ATTRS,
                    "transform": f"rotate(-90 12 {(PLOT_TOP + PLOT_BOTTOM) / 2})",
                },
            ),
            view_box=f"0 0 {VIEW_WIDTH:.0f} {VIEW_HEIGHT:.0f}",
            width="100%",
            height="auto",
            style={"maxWidth": "24em"},
        ),
        spacing="2",
        align="start",
        width="100%",
    )
