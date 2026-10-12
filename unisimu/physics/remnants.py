"""White-dwarf cooling (realism Phase 7, issue #12).

Mestel's cooling law in Kawaler (1998), arXiv:astro-ph/9802217, Eq. 2.3:

    t_cool = 9.41e6 yr (A/12)^-1 (mu_e/2)^(4/3) mu^(-2/7) (M/M_sun)^(5/7) (L/L_sun)^(-5/7)

-- the time a white dwarf of mass M needs to fade to luminosity L. It leaves
out neutrino cooling (hot, young dwarfs), crystallisation and Debye cooling
(the faint end); Kawaler calls it "within 30%" of detailed models. See
docs/physics/equations/07-tracks-remnants.md.
"""

MESTEL_PREFACTOR_YEARS = 9.41e6
# Kawaler's worked example, used for every white dwarf here (an assumption:
# real masses and core compositions vary): a 0.6 M_sun carbon/oxygen core.
WHITE_DWARF_MASS_MSUN = 0.6
CORE_ATOMIC_WEIGHT = 14.0  # 50/50 carbon/oxygen
ELECTRON_MOLECULAR_WEIGHT = 2.0
ENVELOPE_MOLECULAR_WEIGHT = 1.4


def _mestel_scale_years(mass_msun: float = WHITE_DWARF_MASS_MSUN) -> float:
    return (
        MESTEL_PREFACTOR_YEARS
        * (CORE_ATOMIC_WEIGHT / 12.0) ** -1
        * (ELECTRON_MOLECULAR_WEIGHT / 2.0) ** (4.0 / 3.0)
        * ENVELOPE_MOLECULAR_WEIGHT ** (-2.0 / 7.0)
        * mass_msun ** (5.0 / 7.0)
    )


def cooling_time_years(luminosity_lsun: float, mass_msun: float = WHITE_DWARF_MASS_MSUN) -> float:
    """Mestel: years for a white dwarf to fade to `luminosity_lsun`."""
    if luminosity_lsun <= 0:
        raise ValueError("luminosity must be positive")
    return _mestel_scale_years(mass_msun) * luminosity_lsun ** (-5.0 / 7.0)


def cooled_luminosity_lsun(
    years_since_birth: float, birth_luminosity_lsun: float, mass_msun: float = WHITE_DWARF_MASS_MSUN
) -> float:
    """Luminosity `years_since_birth` after the dwarf appeared at
    `birth_luminosity_lsun`: it continues along the Mestel curve from the
    point where it already has that luminosity, so the hand-off from the
    previous stage is continuous."""
    if years_since_birth < 0:
        raise ValueError("time cannot be negative")
    t = cooling_time_years(birth_luminosity_lsun, mass_msun) + years_since_birth
    return (t / _mestel_scale_years(mass_msun)) ** (-7.0 / 5.0)
