# Physics reference: equations and sources

This folder is the research step that comes **before** any code changes for the realism upgrade.
Each file gives the equations a phase needs, with symbols, units, sources and sanity values.

**Verification rule.** A source is marked **Verified** only if it was opened in this research pass and the formula was read in it.
Anything typed from memory or taken from the brief without being opened is marked **unverified**. It must be checked before it goes into code.

| File | Topic | Phase |
|---|---|---|
| [01-radiometry-color.md](01-radiometry-color.md) | Planck, CIE 1931 fit, XYZ→sRGB, Stefan–Boltzmann, magnitudes | 1 |
| [02-starfield.md](02-starfield.md) | HYG v4.2, B−V→T, magnitude→flux, PSF | 2 |
| [03-stellar-surface.md](03-stellar-surface.md) | Limb darkening, H_p, granulation, spots, pulsation | 3 |
| [04-black-hole.md](04-black-hole.md) | Schwarzschild orbits, shadow, lookup tables, redshift g, thin disc | 4 |
| [05-death-scenes.md](05-death-scenes.md) | SN II-P plateau + ⁵⁶Ni/⁵⁶Co tail, PN expansion, line colours, NS | 5 |
| [06-time.md](06-time.md) | Cinematic clock vs true time | 6 |
| [07-tracks-remnants.md](07-tracks-remnants.md) | MIST, red-dwarf evolution, Mestel WD cooling | 7 |

## Corrections this research made to the build prompt
1. **Test count:** on the `realism/phase-0-audit` branch, `pytest tests/ -q` passes **128** tests (43 test functions, expanded by parametrize). The brief said 122, which was the count at f1eb370.
2. **Limb darkening:** Howarth arXiv:1511.02029 is *Reeve & Howarth*, and covers **hot stars only (15–55 kK)**. Cool stars need Claret & Bloemen 2011 (VizieR J/A+A/529/A75; coverage still unverified).
3. **Planetary nebulae:** the true expansion speed is about **42 km/s** and the visibility time about **21 000 ± 5000 yr** (Jacob et al. 2013). The brief's 20–30 km/s and 10⁴ yr are the older spectroscopic values.
4. **Issue #11 threshold:** the "no red giant" mass is **0.25 M☉** (Laughlin, Bodenheimer & Adams 1997, via Adams et al. 2004). The ~0.35 M☉ figure in the brief is the *fully convective* limit, which is a different thing.
5. **MIST:** the site moved to mist.science and states "All rights reserved", with no open licence. Ask before bundling (**new decision D6**).
6. **Disc temperature:** Bruneton uses the Shakura–Sunyaev-type profile T⁴ ∝ r⁻³(1 − √(r_in/r)), not full Novikov–Thorne. Label it "simplified".
7. **Mestel check:** the prefactor reproduces Kawaler's worked example only to within 19 % (open item, see 07 §3).
8. **Solar temperature:** the code uses T☉ = 5778 K, while the IAU nominal value is 5772 K. Leave it unchanged unless the owner approves.

## Opened sources
| Source | Link |
|---|---|
| Wyman, Sloan & Shirley 2013, JCGT 2(2) | https://jcgt.org/published/0002/02/01/ |
| Ballesteros 2012, EPL 97, 34008 | https://arxiv.org/abs/1201.1809 |
| NIST CODATA 2022: h, σ | https://physics.nist.gov/cuu/Constants/ |
| ICC sRGB registry | https://registry.color.org/rgb-registry/srgb |
| IAU 2015 Resolution B2 (bolometric magnitudes) | https://arxiv.org/abs/1510.06262 |
| HYG database (v4.2, CC BY-SA 4.0) | https://www.astronexus.com/projects/hyg |
| Reeve & Howarth 2016 | https://arxiv.org/abs/1511.02029 |
| Magic et al. 2013 (Stagger grid) | https://arxiv.org/abs/1302.2621 |
| Mathur et al. 2011 (red-giant granulation) | https://arxiv.org/abs/1109.1194 |
| Bruneton 2020 | https://arxiv.org/abs/2010.08735 |
| James et al. 2015 | https://arxiv.org/abs/1502.03808 |
| Sahu et al. 2022, ApJ 933, 83 | https://arxiv.org/abs/2201.13296 |
| Vartanyan et al. 2025 | https://arxiv.org/abs/2411.03434 |
| Dessart & Hillier 2011 | https://arxiv.org/abs/1008.3238 |
| Yao et al. 2020 (quotes Nadyozhin 1994 decay rates) | https://arxiv.org/abs/2005.12922 |
| NNDC NuDat 3 half-lives (⁵⁶Ni, ⁵⁶Co) | https://www.nndc.bnl.gov/nudat3/ |
| Jacob, Schönberner & Steffen 2013 | https://arxiv.org/abs/1307.6189 |
| Kawaler 1998 (Mestel cooling) | https://arxiv.org/abs/astro-ph/9802217 |
| Choi et al. 2016 (MIST I) | https://arxiv.org/abs/1604.08592 |
| MIST website | https://mist.science/ |
| Adams, Laughlin & Graves 2004 | https://www.astroscu.unam.mx/rmaa/RMxAC..22/PDF/RMxAC..22_adams.pdf |
| "The M4 Transition" 2011 (fully convective limit) | https://arxiv.org/abs/1012.2580 |

## Still to verify before the phase that needs it
| Item | Needed for | Status |
|---|---|---|
| IAU 2015 B3 (T☉ = 5772 K, R☉) | Phase 1 | not opened |
| CODATA G | Phase 3 | not opened |
| HYG field list | Phase 2 | not opened |
| Claret & Bloemen 2011 ReadMe | Phase 3 | not opened |
| Sunspot ΔT | Phase 3 | unverified |
| Granule-size factor for supergiants | Phase 3 | unverified |
| Pulsation constant Q | Phase 3 | unverified |
| Coronal brightness ratio | Phase 3 | unverified |
| Novikov–Thorne / Page–Thorne | Phase 4 | not opened |
| SN plateau photospheric T | Phase 5 | unverified |
| PN line wavelengths (NIST) | Phase 5 | unverified |
| PN ionisation threshold | Phase 5 | unverified |
| Neutron-star radius and temperature | Phase 5 | unverified |
| Nadyozhin 1994 original | Phase 5 | not opened |
| LBA 1997 original | Phase 7 | not opened |
