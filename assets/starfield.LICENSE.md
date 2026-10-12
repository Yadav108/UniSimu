# `starfield.bin`: licence and attribution

**This file is not covered by the repository's MIT licence.**

`assets/starfield.bin` is derived from the **HYG Database v4.2**, published by astronexus.com (David Nash):
https://www.astronexus.com/projects/hyg (also at https://codeberg.org/astronexus/hyg).

The HYG Database is licensed under the
[Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/)
(CC BY-SA 4.0). Because `starfield.bin` is an adapted version of it, **`starfield.bin` is likewise licensed under CC BY-SA 4.0**.

## What was changed from the original
`tools/build_starfield.py` generated the file from `hygdata_v42.csv.gz` with these steps:
- **Removed:** the Sun (row 0), every star without a V magnitude, and every star fainter than V = 9.0.
- **Stars with V ≤ 6.5** (8920 stars):
  - RA/Dec become a unit direction vector in a scene frame with the celestial pole "up";
  - V magnitude becomes flux relative to V = 0;
  - the B−V colour index becomes a temperature (Ballesteros 2012), then a linear sRGB colour;
  - stars are sorted brightest first and packed as float32.
- **Stars with 6.5 < V ≤ 9.0** are summed into a 128 × 64 equirectangular brightness map, smoothed toward the poles.

The data was not otherwise altered. Positions, magnitudes and colour indices are as published in HYG v4.2.

## Reusing it
You may share and adapt `starfield.bin` under CC BY-SA 4.0. Credit the HYG Database as above, say what you changed, and release your adaptation under the same licence.

The code that reads and renders the file stays MIT.
