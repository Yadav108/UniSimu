"""Approximate blackbody radiation color as a function of temperature.

Uses the Tanner Helland piecewise-polynomial fit to Mitchell Charity's
blackbody data, valid over roughly 1000K-40000K (the full range our
stellar stages span, from cool protostars/remnants to supernova flashes).
"""

import math


def _clamp(value: float, lo: float = 0.0, hi: float = 255.0) -> float:
    return max(lo, min(hi, value))


def kelvin_to_rgb(temperature_k: float) -> tuple[int, int, int]:
    temp = _clamp(temperature_k, 1000.0, 40000.0) / 100.0

    if temp <= 66:
        red = 255.0
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
        red = _clamp(red)

    if temp <= 66:
        green = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    green = _clamp(green)

    if temp >= 66:
        blue = 255.0
    elif temp <= 19:
        blue = 0.0
    else:
        blue = 138.5177312231 * math.log(temp - 10) - 305.0447927307
        blue = _clamp(blue)

    return (round(red), round(green), round(blue))


def kelvin_to_hex(temperature_k: float) -> str:
    r, g, b = kelvin_to_rgb(temperature_k)
    return f"#{r:02x}{g:02x}{b:02x}"
