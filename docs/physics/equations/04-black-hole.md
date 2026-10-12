# 04 — Schwarzschild black hole: lensing, shadow, thin disc

Used by: Phase 4.

## Why
The current black hole has three problems:
- **Fake lensing:** it is a camera-facing billboard (`LENS_FRAG`) with a Gaussian "photon ring" at an invented radius and |sin θ|^1.4 arcs. Nothing is ray traced.
- **Unconditional disk:** every black hole gets a bright accretion disk.
- **Wrong scale:** the horizon radius is a stylized 0.6.

## 0. Isolated black holes are dark (decision D2)
Sahu et al., *An Isolated Stellar-Mass Black Hole Detected Through Astrometric Microlensing*, ApJ 933, 83 (2022), arXiv:2201.13296 (PDF opened). **Verified.**
- They state: "We show that the lens emits no detectable light".
- They also note that isolated black holes "emit no light of their own, and the accretion rate [from the ISM is] too low to produce detectable X-ray or radio emission".

So **default physical mode draws only the shadow plus the lensed starfield**. The disc appears only under a labelled
"with companion / accretion" scenario.

## 1. Metric and photon orbits
Bruneton, *Real-time High-Quality Rendering of Non-Rotating Black Holes*, arXiv:2010.08735 (2020) (PDF opened, §3.1–3.4). **Verified.**

Bruneton works in units where r_s = 2GM/c² = 1 and c = 1. Metric (his Eq. 1):

$$ds^2=(1-\tfrac{1}{r})dt^2-(1-\tfrac{1}{r})^{-1}dr^2-r^2d\theta^2-r^2\sin^2\theta\,d\varphi^2$$

Orbit equation (his Eq. 8), with u = 1/r and e = 1/b (the inverse impact parameter):

$$\Big(\frac{du}{d\varphi}\Big)^2=e^2-u^2(1-u),\qquad u''=\tfrac32u^2-u$$

**Converted to G = c = 1 and mass M** (r_s = 2M, so u_Bruneton = 2M·u). This gives the familiar form

$$u''+u=3Mu^2.$$

The conversion is **derived here**. Check it by substitution: with u = U/(2M), U'' = 1.5U² − U turns into u'' = 3Mu² − u.

Key radii and impact parameter (Bruneton §3.3.1 gives the photon sphere at u = 2/3, i.e. r = 1.5 r_s = 3M, and the critical e² = 4/27):

| Quantity | Units of M | Units of r_s | Source |
|---|---|---|---|
| Horizon r_h | 2M | 1 | metric (Eq. 1) |
| Photon sphere | 3M | 1.5 | Bruneton §3.3.1 |
| Critical impact parameter b_c | 3√3 M ≈ **5.196 M** | √(27/4) ≈ 2.598 | e² = 4/27 ⇒ b = √27/2 r_s |
| ISCO | 6M | 3 | Bruneton §3.3.3 ("r_ic ≥ 3, the innermost stable circular orbit") |

Rays with b < b_c fall in, so they are black: that is the shadow. Rays with b > b_c reach a turning point u_a, given in closed form by Bruneton's Eq. 9:

$$u_a=\tfrac13+\tfrac23\sin\!\Big(\tfrac13\arcsin\!\big(\tfrac{27}{2}e^2-1\big)\Big)$$

This is in r_s units. The "27/2" should be **re-checked against the PDF**: extracted text lost some glyphs, so treat it as **partly verified**.

## 2. Precomputed tables
This is Bruneton's §3.3.2–3.3.3 and Algorithm 1 (verified as the method).
- **D(e, u):** deflection of rays coming from infinity. It gives each pixel's escape direction in O(1), and the escape direction samples the starfield.
- **U(e, φ):** u along the ray, used to find where the ray crosses the disc plane. There are at most two crossings per ray (plus symmetry).
- Both tables also store the coordinate time t (dt/dφ = e/(u² − u³)), which is needed for the disc's retarded-time animation.
- Precompute offline with numpy/scipy (RK45 or similar, at high accuracy) and ship them as a small float texture.

The paper maps the table domains non-linearly for precision; see its Appendix A.

## 3. Lensing magnification (point stars)
Bruneton §3.4.1: a point source is amplified by the solid-angle ratio dΩ_camera/dΩ_emitter, computed from screen-space derivatives (his Eq. 10). This does **not** apply to extended sources such as the disc, because surface brightness is conserved.

## 4. Frequency shift and intensity transfer
Bruneton §3.4.2 (Eq. 11): ν_obs/ν_em = g(k, l)/g(k′, l′). That is the ratio of the photon 4-momentum projected onto the receiver's and the emitter's 4-velocities.

Liouville's theorem: I_ν/ν³ is invariant along a ray. Bruneton cites MTW73 for this. **Verified**, as stated in Bruneton §3.4.2.
It follows that:
- The bolometric intensity transforms as **I_obs = g⁴ I_em**.
- A blackbody at T is observed as a blackbody at **gT**.

### Circular-orbit emitter (derivation for Phase 4; check against Bruneton's Eq. 11 when implementing)
In G = c = 1 units, a gas element on a circular equatorial orbit has:
- angular velocity Ω = √(M/r³);
- u^t = 1/√(1 − 3M/r).

The photon is described by conserved E = −p_t and L_z = p_φ. Write λ ≡ L_z/E, which equals the signed impact parameter projected on the orbital axis.

For an observer at rest at infinity:

$$g=\frac{\nu_{\rm obs}}{\nu_{\rm em}}=\frac{-p_\mu u^\mu_{\rm obs}}{-p_\mu u^\mu_{\rm em}}=\frac{E}{u^t(E-\Omega L_z)}=\frac{\sqrt{1-3M/r}}{1-\Omega\lambda}$$

For a static observer at finite radius r_o, multiply by 1/√(1 − 2M/r_o) (blueshift falling in).

**Status:** derived from first principles. It matches the brief's formula. Bruneton's general Eq. 11 contains it as a special case. **Mark as derived; verify numerically in tests** by comparing with a direct 4-vector computation.

Illustrative numbers at the ISCO (r = 6M), computed:
- λ = 0 (face-on emission): g = √(1/2) = 0.7071, the pure gravitational and transverse redshift.
- λ = ±b_c (the extreme case): g = 1.094 (approaching side) vs 0.522 (receding side).
- So g⁴ = 1.43 vs 0.075, about 19× brighter on the approaching side.

The actual λ comes from the traced ray.

## 5. Thin-disc temperature profile
Bruneton (§3.3.3, "Emitted light") uses a blackbody with T⁴(u) ∝ u³(1 − √(3u)) in r_s units, citing [Las16]. The text was partly garbled in extraction but legible enough to read.

In M units this is

$$T(r)^4\propto r^{-3}\Big(1-\sqrt{r_{\rm in}/r}\Big),\qquad r_{\rm in}=6M.$$

That is the Newtonian Shakura–Sunyaev zero-torque profile, **not** full Novikov–Thorne (which adds relativistic correction factors).
The brief asks for "Novikov–Thorne-like", and this simplified form satisfies that. Novikov & Thorne (1973) and Page & Thorne (1974) are **not opened**: **unverified**. Label the profile "simplified" in the phase note.

Peak T at r ≈ (49/36)·r_in ≈ 8.17M. This is **derived** by setting d/dr[r⁻³(1 − √(r_in/r))] = 0.

The normalisation (accretion rate) is a scenario parameter, not something the star's history determines.

## 6. Out of scope: Kerr
James, von Tunzelmann, Franklin & Thorne, CQG 32, 065001 (2015), arXiv:1502.03808. The PDF was downloaded and the title confirmed ("Gravitational Lensing by Spinning Black Holes in Astrophysics, and in the Movie Interstellar"). Reference only.

## 7. Display scale
The remnant mass is 0.35 M_initial (`stellar.py` constant), and R_s = 2.953 km per M☉ (code constant). The code constant matches 2GM☉/c² = 2.953 km; that arithmetic is **derived**.

On screen, the horizon must be drawn at r_h = 2M relative to the camera distance in the same units. The shadow's angular radius then follows from b_c (approximately b_c/d_cam for a distant camera).

**Tests (Phase 4):**
- Shadow radius in pixels vs 3√3 M·focal/d at several distances.
- The constants 2M, 3M, 6M and b_c.
- g → 1 as r → ∞ with λ = 0.
- g⁴ ratio of approaching to receding sides vs the formula.
- No disc when the flag is off.

## 8. Phase 4 verification (sources opened while implementing)
- **Shadow size (verified).** Synge's formula for a static observer at r_O is
  sin α_sh = 3√3 M √(1 − 2M/r_O) / r_O
  (Perlick & Tsupko 2022, *Calculating black hole shadows*, arXiv:2105.07101, Eqs. 2 and 6, opened). It tends to b_c/r_O far away.
- **Disc redshift (verified).** Bruneton 2020, Eq. 13, gives the circular-orbit emitter 4-velocity in r_s units: k′ = (√(2/(2−3u)), 0, 0, √(u³/(2−3u))). In M units that is u^t = 1/√(1−3M/r) and Ω = √(M/r³). His Eq. 14 and the remark "for black bodies … T′ = (ν/ν′) T" confirm the formula derived in §4,
  g = √(1−3M/r) / (1 − Ωλ),
  and that a blackbody disc is seen as a blackbody at gT.
- **Integrator (verified against both).** `relativity.trace_ray` runs RK4 on u″ = 3Mu² − u. Two checks:
  - The traced shadow edge matches Synge's formula to 4 decimal places at 10, 30 and 100 M.
  - The bending at b = 1000 M is 4M/b within 0.3 %.
  The GLSL shader uses the identical scheme. In a GPU render, the shadow measured **113.0 px against Synge's 112.3 px** at r = 29 M (see the phase note).
- **Disc temperature.** Still the simplified T⁴ ∝ r⁻³(1 − √(r_in/r)) profile from Bruneton §3.3.3. **Not** full Novikov–Thorne; Page & Thorne (1974) was not opened.
- **Companion-disc peak temperature.** 10⁷ K (~1 keV) is an **unverified** order of magnitude, used as a labelled scenario parameter.

