# 05 — Death scenes: Type II-P supernova, planetary nebula, neutron star

Used by: Phase 5.

## Why
The current death scenes are keyframed:
- **Supernova:** in `stellar.py` the luminosity rises over 7 % of the stage, then decays as exp(−5x) while T falls from 60 kK to 6 kK. In the JS, the flash, shock-shell and ejecta timings are fractions of `stage_progress`.
- **Planetary nebula:** an fbm shell that grows from 0.8 to 5.0 in teal and pink.
- **Neutron star:** drawn at a fixed visual radius of 0.075, with sweeping beams always on.

---

## A. Core-collapse supernova, Type II-P

### A1. Plateau ≈ 100 days
- **Vartanyan, Tsang, Kasen, Burrows et al.**, *A 3D Simulation of a Type II-P Supernova: from Core Bounce to Beyond Shock Breakout*, arXiv:2411.03434 (PDF opened). **Verified.**
  - The setup is a 17 M☉ progenitor, 10⁵¹ erg and 0.1 M☉ of ⁵⁶Ni.
  - Shock breakout comes about 1 day after collapse.
  - Ni velocities at breakout reach up to 7000 km s⁻¹.
  - The ejecta are "largely neutral near the end of the plateau (∼100 days)" (Fig. 15 caption).
  - The plateau luminosity varies by about 2× with viewing angle.
- **Dessart & Hillier (2011)**, MNRAS, arXiv:1008.3238 (PDF opened). **Verified.**
  - The abstract describes a "near-constant luminosity up to >100 d after the explosion".
  - §4 gives a plateau "length on the order of 100–150 d" (15 and 25 M☉ models).
  - Fading at the end of the plateau takes about a month to reach the decay curve, at 140–160 d.
  - The paper also notes that the observed SNe it cites (Smartt 2009) drop by about 1 mag around 120 d.

**Model parameters:** plateau duration t_p = 100 d (range 80–150 d, set by the scenario), then a fall over about 10–30 d onto the radioactive tail.

### A2. Radioactive tail: ⁵⁶Ni → ⁵⁶Co → ⁵⁶Fe
Specific heating rate in erg g⁻¹ s⁻¹, from Yao et al. 2020 (SN2019dge), arXiv:2005.12922, Appendix B.3, Eqs. B4–B6 (PDF opened). They attribute it to Nadyozhin (1994). **Verified** as quoted by Yao; the Nadyozhin 1994 original (ApJS 92, 527) was **not opened**.

$$\varepsilon(t)=\varepsilon_{\rm Ni}e^{-t/\tau_{\rm Ni}}+\varepsilon_{\rm Co}\big(e^{-t/\tau_{\rm Co}}-e^{-t/\tau_{\rm Ni}}\big)$$

with ε_Ni = 3.90 × 10¹⁰, ε_Co = 6.78 × 10⁹ erg g⁻¹ s⁻¹, τ_Ni = 8.8 d and τ_Co = 111.3 d. Then L_decay(t) = M_Ni · ε(t), assuming full γ-ray trapping. Dessart & Hillier find no γ escape up to more than 500 d in SNe II-P.

**Cross-check of the lifetimes against NNDC NuDat 3** (both opened): t½(⁵⁶Ni) = 6.075 d and t½(⁵⁶Co) = 77.236 d.
Since τ = t½/ln 2, that gives τ = 8.764 d and 111.43 d, consistent with 8.8 and 111.3. **Verified.**

Sanity values for M_Ni = 1 M☉ (scale linearly; e.g. 0.1 M☉ gives ×0.1):

| t (d) | L_decay (erg s⁻¹) |
|---|---|
| 0 | 7.76 × 10⁴³ |
| 50 | 8.82 × 10⁴² |
| 100 | 5.49 × 10⁴² |
| 200 | 2.24 × 10⁴² |
| 300 | 9.11 × 10⁴¹ |

### A3. Photosphere radius and temperature (simplified)
- Homologous expansion: R_ph(t) ≈ v_ph·t, with v_ph of order 3000–7000 km s⁻¹ (Vartanyan's Ni velocities give the scale).
- The photosphere recedes in mass coordinate during the plateau (Dessart & Hillier §3), so v_ph declines slowly. A constant v is the **documented simplification**.
- T_ph follows from Stefan–Boltzmann: T = (L / 4πR²σ)^{1/4}.
- During the plateau T_ph sits near the hydrogen recombination temperature, roughly 5000–6000 K. That number is **unverified** (the papers describe recombination but I did not extract a T); verify it in Phase 5.
- Colour then comes from doc 01, so there are no keyframed tints.

**Shock breakout:** a brief UV/X-ray flash, about a day after core bounce in the 3D model. In the visible band, render it as a short, very hot blackbody pulse. Its exact duration and peak T are **unverified**; mark the pulse illustrative.

**Function to add:** `supernova_state(t_days, M, R_progenitor) -> (L, T, R_ph)`, labelled "simplified, not radiative transfer".

---

## B. Planetary nebula

### B1. Expansion speed and visibility time
Jacob, Schönberner & Steffen, *The evolution of planetary nebulae VIII. True expansion rates and visibility times*, A&A (2013), arXiv:1307.6189 (PDF opened). **Verified.**

**Correction to the brief:** the brief says 20–30 km s⁻¹ and about 10⁴ yr. The paper finds:
- the commonly used *spectroscopic* velocities run at about 10–30 km s⁻¹;
- the **true expansion of the outer edge averages 42 km s⁻¹**, "nearly twice as high as the commonly adopted value";
- the **visibility time to R = 0.9 pc is 21 000 ± 5000 yr**, for all central-star masses ("a nebula does not become extinct as the central star fades");
- post-AGB stars of about 0.6 M☉ cross the HR diagram in under 10⁴ yr.

**Model parameters:**
- R_shell(t) = v·t, with v = 42 km s⁻¹ (true edge) by default.
- The shell fades as its surface brightness drops. Use Σ ∝ R⁻ᵅ with α derived from their Fig. 4 slope, which is **unverified** until read off the figure.
- Visibility ends near R ≈ 0.9–1 pc.

### B2. Ionisation onset
The brief says the shell starts to glow when the core passes about 30 kK and the core heats toward 10⁵ K.

The 30 kK threshold is **unverified**. The paper discusses ionisation as a function of the central-star track but doesn't give a single threshold. In Phase 5, take it from a cited post-AGB track (e.g. Miller Bertolami 2016, not opened) or keep it as a documented parameter.

### B3. Line colours
| Line | Air wavelength (nm) | Hue |
|---|---|---|
| [O III] | 500.7 | green-cyan |
| Hα | 656.3 | red |
| [N II] | 658.3 | deep red |

These wavelengths are from the brief, **unverified**; confirm them against the NIST Atomic Spectra Database in Phase 5.

Each line is a narrow Gaussian (or delta) fed through the doc 01 CIE path. The shell colour is a weighted sum of those lines. The weights (line ratios) are a scenario parameter, typically [O III] dominant in the inner, high-excitation zone. That is **unverified**; document it as a parameter.

---

## C. Neutron star
The brief's numbers (radius about 10–12 km, surface about 10⁶ K, visible beam being a radio phenomenon) are all **unverified in this session**. The repo uses R = 1.7 × 10⁻⁵ R☉ ≈ 11.8 km and T = 10⁶ K, consistent with the brief.

In Phase 5, cite a review (e.g. Özel & Freire 2016, ARA&A, for radii) before relying on them.

At 10⁶ K the Planck peak is in soft X-rays. The visible colour is the Rayleigh–Jeans tail, i.e. the 100 kK+ blue limit in doc 01's table, at a tiny surface area. The beam stays as a labelled, illustrative toggle.
