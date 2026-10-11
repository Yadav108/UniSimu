# 07 — Stellar tracks, low-mass evolution and white-dwarf cooling

Used by: Phase 7 (optional data layer). It also bears on open issues #11 and #12.

## 1. MIST tracks
Choi et al., *MESA Isochrones and Stellar Tracks (MIST) I: Solar-scaled models*, ApJ 823, 102 (2016), arXiv:1604.08592 (PDF opened). **Verified.**

- **Coverage:** masses **0.1–300 M☉**, log Age 5–10.3, [Z/H] −2.0 to +0.5.
- **Evolution:** "continuously evolved from the pre-main sequence (PMS) to the end of hydrogen burning, the white dwarf cooling sequence, or the end of carbon burning, depending on the initial mass".
- **Primary EEP phase labels:** PMS, ZAMS, IAMS, TAMS, RGBTip, ZACHeB, TACHeB, TP-AGB, post-AGB and WDCS.
  - For massive stars "RGBTip" is retained only for consistency, as their Fig. 4 caption notes.
- **Rotation:** default v/v_crit = 0.4 at ZAMS.

Website: waps.cfa.harvard.edu/MIST **now redirects to https://mist.science/** (opened).
- **Versions:** v1.2 dates from 2018; v2 uses GS98 abundances with [α/Fe]; the latest listed release is **v2.5 (24 Feb 2026)**.
- **Licence:** the site states no licence or citation terms beyond **"All rights reserved"**.

**Do not bundle MIST-derived tables until the owner agrees.** Ideally, email the MIST team for permission, or ship only the offline script and have users download the data. This is decision D6 (new).

**Mapping MIST phases to UniSimu stages**, to define in Phase 7:

| MIST | UniSimu |
|---|---|
| PMS | protostar |
| ZAMS…TAMS | main sequence |
| RGB/CHeB/AGB | red giant or supergiant |
| post-AGB | planetary nebula |
| WDCS | white dwarf |

Massive-star tracks stop at carbon depletion, so the supernova and remnant still come from the existing rule (8 and 20 M☉ thresholds), which needs its own citation in Phase 7.

## 2. Low-mass stars: the issue #11 correction
- Laughlin, Bodenheimer & Adams (1997), ApJ 482, 420 ("LBA"). The original was **not opened**.
- Its results are restated with figures in **Adams, Laughlin & Graves (2004)**, *Red dwarfs and the end of the main sequence*, RevMexAA (SC) 22, 46 (PDF opened). **Verified:**
  - "Red dwarfs turn into blue dwarfs and finally white dwarfs"; they "do not experience red giant phases".
  - The Fig. 2 caption reads: "Stars with mass **M = 0.25 M☉ are the least massive stars that can become red giants**".
  - Lifetimes: about 1 × 10¹² yr at 0.25 M☉, and 12 × 10¹² yr at 0.08 M☉. A 0.1 M☉ star stays convective for 5.74 × 10¹² yr.

**Correction to the brief and issue #11:**
- The **fully convective** boundary is about 0.35 M☉ (Chabrier & Baraffe 1997) or about 0.25 M☉ (Dorman et al. 1989). Both are quoted in arXiv:1012.2580 (opened), which says "most… models predict the transition… at 0.3 M☉".
- The **no-red-giant** threshold (LBA) is **0.25 M☉**.

These are different statements. For the stage track, use 0.25 M☉ as the "no red giant" cut. The fully convective limit matters only for mixing and lifetime.

Proxima (0.12 M☉) should go: MS → blue dwarf (heats up at roughly constant small R) → white dwarf, with no planetary nebula.
Adding the new stage must be additive. `stage_track()` for masses ≥ 0.25 M☉ is unchanged. The existing tests expect Proxima to follow `LOW_MASS_TRACK`, so **ask the owner before changing it** (constraint 8).

## 3. White-dwarf cooling (Mestel): the issue #12 fix
Kawaler (1998), *White dwarf stars and the Hubble Deep Field*, arXiv:astro-ph/9802217, §2.1 Eq. 2.3 (PDF opened). **Verified.**

$$t_{\rm cool}=9.41\times10^{6}\,{\rm yr}\,\Big(\frac{A}{12}\Big)^{-1}\Big(\frac{\mu_e}{2}\Big)^{4/3}\mu^{-2/7}\Big(\frac{M}{M_\odot}\Big)^{5/7}\Big(\frac{L}{L_\odot}\Big)^{-5/7}$$

| Symbol | Meaning |
|---|---|
| A | mean atomic weight of the core (14 for a 50/50 C/O core) |
| μ_e | mean molecular weight per electron (2) |
| μ | envelope mean molecular weight (1.4 in his example) |
| M | WD mass |
| L | WD luminosity |

Inverted for rendering:

$$L(t)=L_\odot\Big[\frac{t}{9.41\times10^{6}\,{\rm yr}\,(A/12)^{-1}(\mu_e/2)^{4/3}\mu^{-2/7}(M/M_\odot)^{5/7}}\Big]^{-7/5}$$

T_eff then follows from Stefan–Boltzmann with the WD radius (the repo uses 0.012 R☉).

**Check:**
- Kawaler states that M = 0.6 M☉, A = 14, μ = 1.4 and L = 10⁻⁴·⁵ L☉ give about **7 × 10⁹ yr**.
- Evaluating the formula as transcribed gives **8.3 × 10⁹ yr**.
- The 19 % gap may come from rounding in the paper or from a glyph lost in the PDF extraction (e.g. the μ exponent). Kawaler adds that Mestel is "within 30 %" of modern cooling ages.
- **Status: formula verified in form; the prefactor/example gap is open.** Re-read the PDF visually in Phase 7, and test against Kawaler's 7 × 10⁹ yr with a 25 % tolerance until it is resolved.

**Known limits** (Kawaler §2.2): the formula ignores neutrino cooling (hot, early WDs), crystallisation (latent heat produces a bump) and Debye cooling (a faster drop at the faint end). Label the curve "Mestel approximation".

## 4. Existing code constants to re-examine (no change without owner approval)
| Constant | Where | Value | Comment |
|---|---|---|---|
| RED_GIANT_TIP_TEMPERATURE_K | `stellar.py:40` | 3200 K | Check against a MIST 1 M☉ track at RGBTip |
| Giant L ×≤1000 | `stellar.py:41-42` | Sun ≈ 1000 L☉, ≈ 103 R☉ | Check against MIST |
| WD | `stellar.py:50-51` | 25 kK, 0.012 R☉, fixed | Replace with Mestel cooling (§3) |
| T☉ | `stellar.py` | 5778 K | IAU nominal value is 5772 K (doc 01 §4) |
