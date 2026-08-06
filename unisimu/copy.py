"""Plain-language explanations shown to the user at key moments -- kept
separate from physics/state logic since this is pure UI copy."""

STAGE_LABELS: dict[str, str] = {
    "protostar": "Protostar",
    "main_sequence": "Main Sequence",
    "red_giant": "Red Giant",
    "red_supergiant": "Red Supergiant",
    "supernova": "Supernova",
    "planetary_nebula": "Planetary Nebula",
    "white_dwarf": "White Dwarf",
    "neutron_star": "Neutron Star",
    "black_hole": "Black Hole",
}

# Radix accent-scale names for the three terminal fates (used as
# rx.badge color_scheme) -- these adapt correctly between light/dark theme
# automatically, unlike a hardcoded hex value.
FATE_COLOR_SCHEMES: dict[str, str] = {
    "white_dwarf": "sky",
    "neutron_star": "violet",
    "black_hole": "bronze",
}

# Hex accents for the three terminal fates against the observatory theme's
# dark palette (see assets/theme.css) -- used by the shelf's fate stamp,
# which needs the theme's actual palette rather than a Radix color_scheme.
FATE_ACCENT_HEX: dict[str, str] = {
    "white_dwarf": "#bfe1f0",
    "neutron_star": "#b79ce8",
    "black_hole": "#c97a5a",
}

STAGE_CAPTIONS: dict[str, str] = {
    "main_sequence": "Gravity and fusion reach equilibrium: the star settles "
    "into a long, stable hydrogen-burning main sequence.",
    "red_giant": "The core runs out of hydrogen. Fusion moves to a shell "
    "around it, and the outer layers swell enormously as a red giant.",
    "red_supergiant": "The core runs out of hydrogen. Fusion moves to a "
    "shell around it, and the outer layers swell into a red supergiant.",
    "supernova": "The core collapses in under a second and rebounds in a "
    "supernova -- briefly outshining its entire host galaxy.",
    "planetary_nebula": "The star sheds its outer layers into space, "
    "exposing its hot, dense core.",
    "white_dwarf": "With no fuel left to fuse, the exposed core settles "
    "into a slowly cooling white dwarf, supported by electron degeneracy "
    "pressure.",
    "neutron_star": "The collapsed core is crushed into a neutron star: "
    "roughly a sun's mass packed into a sphere the size of a city.",
    "black_hole": "The collapsed core is too massive for any known force "
    "to halt its collapse, forming a black hole.",
}
