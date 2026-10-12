"""Human-readable number formatting for the readouts and H-R axes."""

import math

SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def format_scientific(value: float, plain_lo: float = 1e-3, plain_hi: float = 1e5) -> str:
    """Plain notation inside [plain_lo, plain_hi) -- thousands separated,
    4 significant figures below 1000 -- and `m.m×10ⁿ` outside it, e.g.
    2.7×10⁸ instead of 2.737e+08."""
    if value == 0:
        return "0"
    magnitude = abs(value)
    if 1e3 <= magnitude < plain_hi:
        return f"{value:,.0f}"
    if plain_lo <= magnitude < 1e3:
        return f"{value:.4g}"
    exponent = math.floor(math.log10(magnitude))
    mantissa = value / 10**exponent
    return f"{mantissa:.1f}×10{str(exponent).translate(SUPERSCRIPT)}"


DAYS_PER_YEAR = 365.25  # Julian year


def format_duration(years: float) -> str:
    """A span of time in the most readable unit: days below a year, then
    yr / kyr / Myr / Gyr, and scientific notation in Gyr beyond 10^5 Gyr."""
    if years < 0:
        raise ValueError("a duration cannot be negative")
    if years < 1:
        return f"{years * DAYS_PER_YEAR:,.0f} d"
    for unit, scale in (("Gyr", 1e9), ("Myr", 1e6), ("kyr", 1e3)):
        if years >= scale:
            value = years / scale
            if value >= 1e5:
                return f"{format_scientific(value)} {unit}"
            return f"{value:,.3g} {unit}" if value < 1000 else f"{value:,.0f} {unit}"
    return f"{years:,.3g} yr" if years < 100 else f"{years:,.0f} yr"
