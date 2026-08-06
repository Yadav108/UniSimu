"""Named preset stars for the browsable shelf: real, recognizable stars
spanning all three terminal fates, so comparing them side by side makes the
mass-dependent branching of stellar evolution concrete."""

from dataclasses import dataclass

from unisimu.physics.stellar import stage_track


@dataclass(frozen=True)
class StarPreset:
    key: str
    name: str
    mass_msun: float
    blurb: str
    # Each star's real, currently-observed spectral classification -- not
    # derived from mass, since evolved stars (supergiants, LBVs) no longer
    # match their main-sequence type.
    spectral_class: str

    @property
    def fate_stage(self) -> str:
        return stage_track(self.mass_msun)[-1]


PRESETS: list[StarPreset] = [
    StarPreset(
        "proxima",
        "Proxima Centauri",
        0.12,
        "The closest star to the Sun -- a faint red dwarf that will keep "
        "burning for trillions of years.",
        "M5.5V",
    ),
    StarPreset(
        "sun",
        "The Sun",
        1.0,
        "An ordinary G-type star, about halfway through its roughly "
        "10-billion-year main-sequence life.",
        "G2V",
    ),
    StarPreset(
        "sirius",
        "Sirius A",
        2.1,
        "The brightest star in Earth's night sky -- burns hotter and "
        "faster than the Sun.",
        "A1V",
    ),
    StarPreset(
        "betelgeuse",
        "Betelgeuse",
        16.5,
        "A red supergiant nearing the end of its life -- could go "
        "supernova any time in the next hundred thousand years.",
        "M1-2 Ia",
    ),
    StarPreset(
        "rigel",
        "Rigel",
        23.0,
        "A blue supergiant tens of thousands of times more luminous "
        "than the Sun.",
        "B8 Ia",
    ),
    StarPreset(
        "eta_carinae",
        "Eta Carinae",
        90.0,
        "One of the most massive and luminous stars known -- already "
        "unstable, shedding huge amounts of mass.",
        "LBV",
    ),
]
