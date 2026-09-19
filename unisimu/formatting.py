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
