import pytest

from unisimu import hr_geometry
from unisimu.physics.stellar import evolve, main_sequence_luminosity, main_sequence_temperature_k


def _parse_points(svg_points: str) -> list[tuple[float, float]]:
    pairs = svg_points.split(" ")
    return [tuple(float(v) for v in pair.split(",")) for pair in pairs]


@pytest.mark.parametrize("mass_msun", [0.1, 0.3, 1.0, 8.0, 20.0, 90.0, 150.0])
def test_track_polyline_stays_within_plot_bounds(mass_msun):
    points = _parse_points(hr_geometry.track_polyline(mass_msun))
    assert len(points) > 10
    for x, y in points:
        assert hr_geometry.PLOT_LEFT - 1e-6 <= x <= hr_geometry.PLOT_RIGHT + 1e-6
        assert hr_geometry.PLOT_TOP - 1e-6 <= y <= hr_geometry.PLOT_BOTTOM + 1e-6


@pytest.mark.parametrize("mass_msun", [0.1, 1.0, 20.0, 150.0])
def test_marker_position_stays_within_plot_bounds(mass_msun):
    snap = evolve(mass_msun, 0.0)
    x, y = hr_geometry.marker_position(mass_msun, snap.temperature_k, snap.luminosity_lsun)
    assert hr_geometry.PLOT_LEFT - 1e-6 <= x <= hr_geometry.PLOT_RIGHT + 1e-6
    assert hr_geometry.PLOT_TOP - 1e-6 <= y <= hr_geometry.PLOT_BOTTOM + 1e-6


def test_temperature_axis_is_reversed_hot_on_left():
    """A hotter star's main-sequence point should sit further LEFT than a
    cooler one -- the astronomy-standard reversed temperature axis."""
    hot_mass, cool_mass = 20.0, 0.5
    hot_t = main_sequence_temperature_k(hot_mass)
    cool_t = main_sequence_temperature_k(cool_mass)
    assert hot_t > cool_t

    hot_x, _ = hr_geometry.marker_position(hot_mass, hot_t, main_sequence_luminosity(hot_mass))
    cool_x, _ = hr_geometry.marker_position(cool_mass, cool_t, main_sequence_luminosity(cool_mass))
    assert hot_x < cool_x


def test_luminosity_axis_increases_upward():
    """A more luminous point should sit further UP (smaller SVG y) than a
    dimmer one, for the same star's domain."""
    mass = 1.0
    t_domain, l_domain = hr_geometry._domain_for_mass(mass)
    dim_x, dim_y = hr_geometry._to_screen(5000.0, 0.01, t_domain, l_domain)
    bright_x, bright_y = hr_geometry._to_screen(5000.0, 100.0, t_domain, l_domain)
    assert bright_y < dim_y


@pytest.mark.parametrize("mass_msun", [0.1, 1.0, 8.0, 20.0, 150.0])
def test_ticks_are_within_plot_bounds_and_sorted(mass_msun):
    t_ticks = hr_geometry.temperature_ticks(mass_msun)
    l_ticks = hr_geometry.luminosity_ticks(mass_msun)
    assert t_ticks and l_ticks
    xs = [x for x, _ in t_ticks]
    ys = [y for y, _ in l_ticks]
    # Both tick lists are ascending in physical value; temperature's axis
    # is reversed (hot on the left) and luminosity increases upward, so
    # both map to descending screen coordinates.
    assert xs == sorted(xs, reverse=True)
    assert ys == sorted(ys, reverse=True)
    for x in xs:
        assert hr_geometry.PLOT_LEFT - 1e-6 <= x <= hr_geometry.PLOT_RIGHT + 1e-6
    for y in ys:
        assert hr_geometry.PLOT_TOP - 1e-6 <= y <= hr_geometry.PLOT_BOTTOM + 1e-6


def test_collapsed_remnant_does_not_blow_out_the_domain():
    """The final (remnant) sample is deliberately excluded from domain
    fitting -- otherwise a neutron star's placeholder ~50 K would stretch
    every star's axis across a near-useless range."""
    t_domain, _ = hr_geometry._domain_for_mass(8.0)
    span_dex = t_domain[1] - t_domain[0]
    assert span_dex < 3.0
