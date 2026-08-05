"""Plain-language explanations shown to the user at key moments -- kept
separate from physics/state logic since this is pure UI copy."""

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
