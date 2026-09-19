"""Observatory-logbook style tokens shared by the shelf and the detail page.

Colors live as CSS custom properties in assets/theme.css (`--uni-*`); this
module holds the pieces that need to be Python values: the font stacks and
the bordered "stamp" label used for a star's stage/fate.
"""

# Keep in sync with --uni-serif / --uni-mono in assets/theme.css.
SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif"
MONO = "'SF Mono', Consolas, Menlo, monospace"

# A small, uppercase, hairline-bordered label -- e.g. "RED GIANT". Callers
# add their own border/color so a stamp can carry a fate or a stage accent.
STAMP = {
    "font_size": "0.6875em",
    "letter_spacing": "0.08em",
    "text_transform": "uppercase",
    "padding": "0.3em 0.65em",
    "white_space": "nowrap",
}
