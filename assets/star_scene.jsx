import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";

// No React import, and no useRef/useEffect: this file is loaded as a raw
// dynamic asset (Reflex's `$/public/...` NoSSRComponent path), which Vite's
// dev-server dependency crawler can't see ahead of time. On a cold load it
// discovers "react" as a new dependency mid-session and optimizes a second,
// separate copy of it -- one whose hooks dispatcher was never wired up by
// the react-dom instance actually doing the rendering, so any hook call
// here (even just useRef) throws "Cannot read properties of null (reading
// 'useRef')". A plain callback `ref` prop sidesteps this entirely: React
// invokes it directly as a function during commit, without going through
// the hooks dispatcher, so it works no matter which copy of react this
// module resolves against.

// Imperative vanilla Three.js -- NOT @react-three/fiber. Fiber's custom
// React renderer depends on react-reconciler reaching into React's private
// shared-internals object, whose field names changed in recent React 19.2.x
// releases (e.g. the old `ReactCurrentOwner` key is gone), which currently
// crashes react-reconciler@0.33 (the version @react-three/fiber@9 bundles)
// on import. Plain Three.js has no dependency on React internals at all,
// so it sidesteps that whole compatibility gap.

// Everything lives in this one file on purpose: reflex only copies the
// asset it was pointed at (rx.asset), so sibling modules wouldn't resolve.
//
// Layout: helpers -> GLSL -> material factories -> mountStarScene() (scene
// construction, then the per-frame stage state machine in animate()).

const SPACE_COLOR = 0x03040a; // keep in sync with components/viewport.py

const { clamp, lerp, smoothstep } = THREE.MathUtils;
const easeOutCubic = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
// Frame-rate-independent exponential smoothing toward a target.
const damp = (current, target, rate, delta) => lerp(current, target, 1 - Math.exp(-rate * delta));

// Physical radius spans ~9 orders of magnitude (black hole to red
// supergiant), so it's mapped onto a bounded visual scale: a power law
// below 1 Rsun (so a white dwarf reads as clearly smaller than a dwarf
// star), a log above it, and a soft saturation past ~100 Rsun so even the
// largest supergiants keep visibly growing instead of pinning at a clamp.
function visualScale(radiusRsun) {
  const r = Math.max(radiusRsun, 0);
  if (r < 1) return Math.max(0.05, 0.72 * Math.pow(r, 0.33));
  const base = Math.log1p(r) * 0.6 + 0.3;
  if (base <= 2.5) return base;
  return 2.5 + 1.2 * (1 - Math.exp(-(base - 2.5) / 1.6));
}

// Real stars' rotation varies by orders of magnitude across their life --
// most dramatically, a collapsed core conserves the angular momentum of a
// much larger star, so neutron stars can spin hundreds of times per second
// (pulsars). Values here are stylized, not literal, but the relative
// ordering (giants slow, neutron stars fast) is physically motivated.
const ROTATION_SPEED_BY_STAGE = {
  protostar: 0.05,
  main_sequence: 0.12,
  red_giant: 0.04,
  red_supergiant: 0.04,
  supernova: 0.3,
  planetary_nebula: 0.06,
  white_dwarf: 0.3,
  neutron_star: 6.0,
  black_hole: 0.02,
};
const DEFAULT_ROTATION_SPEED = 0.1;

// Per-stage look of the star's own surface: granulation scale, brightness
// variation, sunspot coverage, and how streaky its corona is.
const SURFACE_BY_STAGE = {
  protostar: { cell: 3.0, contrast: 0.9, spots: 0.0, rays: 0.3, intensity: 0.8, blotch: 0.4 },
  main_sequence: { cell: 7.0, contrast: 1.0, spots: 1.0, rays: 1.0, intensity: 1.1, blotch: 0.1 },
  red_giant: { cell: 2.3, contrast: 1.0, spots: 0.6, rays: 0.35, intensity: 0.95, blotch: 0.8 },
  red_supergiant: { cell: 2.0, contrast: 1.0, spots: 0.7, rays: 0.35, intensity: 0.95, blotch: 1.0 },
  supernova: { cell: 4.0, contrast: 0.7, spots: 0.0, rays: 0.9, intensity: 1.0, blotch: 0.1 },
  planetary_nebula: { cell: 3.0, contrast: 0.2, spots: 0.0, rays: 0.8, intensity: 1.1, blotch: 0.1 },
  white_dwarf: { cell: 3.0, contrast: 0.15, spots: 0.0, rays: 0.6, intensity: 1.2, blotch: 0.1 },
  neutron_star: { cell: 3.0, contrast: 0.1, spots: 0.0, rays: 0.5, intensity: 2.0, blotch: 0.1 },
  black_hole: { cell: 3.0, contrast: 0.0, spots: 0.0, rays: 0.0, intensity: 0.0, blotch: 0.1 },
};

// Colours for the two gas palettes the nebula shell can wear.
const PLANETARY_PALETTE = [new THREE.Color(0.2, 0.85, 0.78), new THREE.Color(1.0, 0.28, 0.42)];
const SUPERNOVA_PALETTE = [new THREE.Color(1.0, 0.42, 0.12), new THREE.Color(0.28, 0.6, 1.0)];

const HORIZON_RADIUS = 0.6; // stylized: a real one is ~1e-5 Rsun, invisible
const NEUTRON_STAR_RADIUS = 0.075;

// ---------------------------------------------------------------- GLSL ---

// Hash-based value noise + fbm. Cheap, no textures, and seamless when
// sampled on a unit circle/sphere (which is how the corona and disks use it).
const NOISE_GLSL = `
float hash13(vec3 p3) {
  p3 = fract(p3 * 0.1031);
  p3 += dot(p3, p3.zyx + 31.32);
  return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  float n000 = hash13(i);
  float n100 = hash13(i + vec3(1.0, 0.0, 0.0));
  float n010 = hash13(i + vec3(0.0, 1.0, 0.0));
  float n110 = hash13(i + vec3(1.0, 1.0, 0.0));
  float n001 = hash13(i + vec3(0.0, 0.0, 1.0));
  float n101 = hash13(i + vec3(1.0, 0.0, 1.0));
  float n011 = hash13(i + vec3(0.0, 1.0, 1.0));
  float n111 = hash13(i + vec3(1.0, 1.0, 1.0));
  return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
             mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}
float fbm(vec3 p) {
  float a = 0.5;
  float s = 0.0;
  for (int i = 0; i < 5; i++) {
    s += a * vnoise(p);
    p = p * 2.03 + vec3(1.7, 9.2, 3.3);
    a *= 0.5;
  }
  return s;
}
`;

// Mesh-with-normals vertex shader shared by the star, nebula and beams.
const SURFACE_VERT = `
varying vec3 vObj;
varying vec3 vNormalV;
varying vec3 vViewDir;
void main() {
  vObj = position;
  vNormalV = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vViewDir = -mv.xyz;
  gl_Position = projectionMatrix * mv;
}
`;

const QUAD_VERT = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

// The star itself: self-luminous (no lighting), with limb darkening,
// two-octave convective granulation and slowly drifting starspots. Output is
// HDR (can exceed 1.0) so the bloom pass picks it up.
const STAR_FRAG = `
${NOISE_GLSL}
uniform vec3 uColor;
uniform float uTime, uIntensity, uCellScale, uContrast, uSpots, uLimb, uBlotch;
varying vec3 vObj;
varying vec3 vNormalV;
varying vec3 vViewDir;
void main() {
  vec3 n = normalize(vNormalV);
  float mu = clamp(dot(n, normalize(vViewDir)), 0.0, 1.0);
  vec3 p = normalize(vObj) * uCellScale;
  float g1 = fbm(p + vec3(0.0, uTime * 0.04, 0.0));
  float g2 = fbm(p * 2.6 + vec3(uTime * 0.07, 0.0, -uTime * 0.05));
  float gran = g1 * 0.65 + g2 * 0.35;
  float cells = smoothstep(0.30, 0.72, gran);
  float spotN = fbm(normalize(vObj) * 1.7 + 11.3 + vec3(uTime * 0.005));
  float spot = smoothstep(0.62, 0.78, spotN) * uSpots;
  float blotch = fbm(normalize(vObj) * 1.3 + vec3(uTime * 0.02, 0.0, 3.1));
  float limb = 1.0 - uLimb * (1.0 - mu);
  // Convection cells: bright granule centres, cooler and redder lanes.
  vec3 lane = uColor * vec3(0.9, 0.72, 0.6);
  vec3 col = mix(uColor, mix(lane, uColor * 1.12, cells), uContrast);
  col *= limb;
  col *= 1.0 - 0.7 * spot;
  col *= mix(1.0, 0.45 + 1.3 * blotch, uBlotch);
  col = mix(col * vec3(1.0, 0.72, 0.5), col, smoothstep(0.0, 0.55, mu));
  gl_FragColor = vec4(col * uIntensity, 1.0);
}
`;

// Camera-facing corona/flash: bright at the limb, exponential falloff, with
// angular streamers. uInner is the star's radius as a fraction of the quad's
// half-size (0 for a free-floating flash with no star inside it).
const CORONA_FRAG = `
${NOISE_GLSL}
uniform vec3 uColor;
uniform float uTime, uInner, uIntensity, uRays;
varying vec2 vUv;
void main() {
  vec2 q = (vUv - 0.5) * 2.0;
  float r = length(q);
  float d = max(r - uInner, 0.0) / max(1.0 - uInner, 1e-3);
  float ang = atan(q.y, q.x);
  vec3 dirp = vec3(cos(ang), sin(ang), 0.0);
  float rays = fbm(dirp * 3.2 + vec3(0.0, 0.0, uTime * 0.12 + d * 1.5));
  float rays2 = vnoise(dirp * 9.0 + vec3(uTime * 0.2, 0.0, d * 3.0));
  float streak = mix(1.0, 0.35 + 2.6 * rays * rays2, uRays);
  float glow = exp(-d * 10.0) * 0.9 + exp(-d * 3.8) * 0.16;
  float edge = 1.0 - smoothstep(0.55, 0.95, d);
  float a = glow * streak * edge * uIntensity * step(uInner * 0.98, r);
  gl_FragColor = vec4(uColor * a, 1.0);
}
`;

// Thin, limb-brightened translucent gas shell (planetary nebula, supernova
// remnant, shockwave). Additive, so it reads as emission rather than a solid.
const NEBULA_FRAG = `
${NOISE_GLSL}
uniform vec3 uColorA, uColorB;
uniform float uTime, uOpacity, uSeed, uRim, uClump, uBase;
varying vec3 vObj;
varying vec3 vNormalV;
varying vec3 vViewDir;
void main() {
  vec3 n = normalize(vNormalV);
  float mu = abs(dot(n, normalize(vViewDir)));
  float rim = pow(max(1.0 - mu, 0.0), uRim);
  vec3 dir = normalize(vObj);
  float f = fbm(dir * 3.0 + uSeed + vec3(uTime * 0.03));
  float f2 = fbm(dir * 7.0 - vec3(uTime * 0.05) + uSeed * 2.0);
  float clumps = mix(1.0, smoothstep(0.32, 0.8, f) * 0.85 + f2 * 0.5, uClump);
  vec3 col = mix(uColorA, uColorB, smoothstep(0.3, 0.9, f2 + rim * 0.35));
  float a = (rim * 0.95 + uBase) * clumps * uOpacity;
  gl_FragColor = vec4(col * a, 1.0);
}
`;

// Open cone used for pulsar beams and protostar jets: brightest along its
// axis (view-facing fresnel), fading with distance from the apex.
const BEAM_VERT = `
uniform float uH;
varying vec3 vNormalV;
varying vec3 vViewDir;
varying float vAlong;
void main() {
  vAlong = clamp(-position.y / uH, 0.0, 1.0);
  vNormalV = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vViewDir = -mv.xyz;
  gl_Position = projectionMatrix * mv;
}
`;
const BEAM_FRAG = `
uniform vec3 uColor;
uniform float uOpacity, uFalloff;
varying vec3 vNormalV;
varying vec3 vViewDir;
varying float vAlong;
void main() {
  float mu = abs(dot(normalize(vNormalV), normalize(vViewDir)));
  float core = pow(mu, 1.6);
  float fade = pow(1.0 - vAlong, uFalloff) * smoothstep(0.0, 0.03, vAlong);
  gl_FragColor = vec4(uColor * core * fade * uOpacity, 1.0);
}
`;

// Flat accretion disk in its own XY plane (the mesh is tilted afterward).
// Inner gas is hotter and orbits faster (Keplerian r^-1.5), so the streaks
// visibly shear; uDoppler brightens the approaching side.
const DISK_VERT = `
varying vec2 vPos;
void main() {
  vPos = position.xy;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;
const DISK_FRAG = `
${NOISE_GLSL}
uniform vec3 uColorIn, uColorOut;
uniform float uTime, uIn, uOut, uSpin, uDoppler, uBright, uOpacity, uStreak;
varying vec2 vPos;
void main() {
  float r = length(vPos);
  float th = atan(vPos.y, vPos.x);
  float t = clamp((r - uIn) / (uOut - uIn), 0.0, 1.0);
  float a = th - uTime * uSpin * pow(max(r, 0.6), -1.5);
  vec3 dp = vec3(cos(a), sin(a), 0.0);
  float s1 = fbm(dp * 2.2 + vec3(0.0, 0.0, r * 2.4));
  float s2 = fbm(dp * 6.0 + vec3(0.0, 0.0, r * 8.0));
  float streak = mix(1.0, 0.35 + 1.1 * s1 + 0.6 * s2, uStreak);
  float edgeIn = smoothstep(0.0, 0.06, t);
  float fall = pow(1.0 - t, 1.5);
  float heat = pow(1.0 - t, 1.6);
  vec3 col = mix(uColorOut, uColorIn, heat);
  float dop = max(1.0 + uDoppler * cos(th), 0.05);
  float I = edgeIn * fall * streak * uBright * uOpacity * dop * dop;
  gl_FragColor = vec4(col * I, 1.0);
}
`;

// Camera-facing "gravitational lens" for the black hole: a thin photon ring
// hugging the shadow plus the bent image of the disk's far side arching over
// the top and under the bottom. Coordinates are in horizon radii.
const LENS_FRAG = `
${NOISE_GLSL}
uniform float uTime, uOpacity;
varying vec2 vUv;
void main() {
  vec2 q = (vUv - 0.5) * 6.0;
  float r = length(q);
  float th = atan(q.y, q.x);
  float ringD = (r - 1.12) * 14.0;
  float ring = exp(-ringD * ringD);
  float band = smoothstep(1.06, 1.2, r) * exp(-(r - 1.06) * 2.4);
  float arcs = 0.18 + 0.82 * pow(abs(sin(th)), 1.4);
  float dop = 1.0 + 0.55 * cos(th);
  vec3 dp = vec3(cos(th), sin(th), 0.0);
  float n = fbm(dp * 2.5 + vec3(0.0, 0.0, r * 3.0 - uTime * 0.3));
  float I = (ring * 1.6 + band * arcs * (0.5 + 0.9 * n)) * dop * uOpacity;
  I *= 1.0 - smoothstep(2.4, 3.0, r);
  vec3 col = mix(vec3(1.0, 0.45, 0.12), vec3(1.0, 0.92, 0.75), clamp(ring + band * 0.4, 0.0, 1.0));
  gl_FragColor = vec4(col * I, 1.0);
}
`;

// Round, soft, twinkling background stars; constant on-screen size.
const STARFIELD_VERT = `
attribute vec3 aColor;
attribute float aSize;
attribute float aPhase;
uniform float uPixelRatio, uTime;
varying vec3 vColor;
varying float vTwinkle;
void main() {
  vColor = aColor;
  vTwinkle = 0.82 + 0.18 * sin(uTime * (0.6 + aPhase * 1.7) + aPhase * 40.0);
  gl_PointSize = aSize * uPixelRatio;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;
const POINT_FRAG = `
varying vec3 vColor;
varying float vTwinkle;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  float a = 1.0 - smoothstep(0.0, 1.0, d);
  a *= a;
  gl_FragColor = vec4(vColor * a * vTwinkle, 1.0);
}
`;

// Supernova ejecta: particles fly outward, decelerating, cooling from
// white-hot to deep red and fading out.
const EJECTA_VERT = `
attribute float aSeed;
uniform float uP, uMax, uPixelRatio, uActive;
varying float vAlpha;
varying vec3 vCol;
void main() {
  float e = 1.0 - pow(1.0 - clamp(uP, 0.0, 1.0), 2.6);
  vec3 pos = position * uMax * e;
  float heat = 1.0 - clamp(uP * 1.6 + aSeed * 0.25, 0.0, 1.0);
  vCol = mix(vec3(0.9, 0.22, 0.05), vec3(1.0, 0.85, 0.55), heat * heat) * (0.8 + aSeed * 0.6) * 0.4;
  vAlpha = uActive * smoothstep(0.0, 0.08, uP) * (1.0 - smoothstep(0.35, 0.98, uP));
  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  gl_PointSize = (3.0 + aSeed * 7.0) * uPixelRatio * (8.0 / max(-mv.z, 1.0));
  gl_Position = projectionMatrix * mv;
}
`;
const EJECTA_FRAG = `
varying float vAlpha;
varying vec3 vCol;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  float a = 1.0 - smoothstep(0.0, 1.0, d);
  gl_FragColor = vec4(vCol * a * a * vAlpha, 1.0);
}
`;

// -------------------------------------------------- material factories ---

function shaderMaterial({ vertex, fragment, uniforms, side = THREE.FrontSide, additive = true }) {
  return new THREE.ShaderMaterial({
    vertexShader: vertex,
    fragmentShader: fragment,
    uniforms,
    side,
    transparent: additive,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    depthWrite: !additive,
  });
}

const color = (r, g, b) => ({ value: new THREE.Color(r, g, b) });

function makeStarMaterial() {
  return shaderMaterial({
    vertex: SURFACE_VERT,
    fragment: STAR_FRAG,
    additive: false,
    uniforms: {
      uColor: color(1, 1, 1), uTime: { value: 0 }, uIntensity: { value: 1 },
      uCellScale: { value: 6 }, uContrast: { value: 0.4 }, uSpots: { value: 0 }, uLimb: { value: 0.65 }, uBlotch: { value: 0 },
    },
  });
}

function makeCoronaMaterial(inner) {
  return shaderMaterial({
    vertex: QUAD_VERT,
    fragment: CORONA_FRAG,
    uniforms: {
      uColor: color(1, 1, 1), uTime: { value: 0 }, uInner: { value: inner },
      uIntensity: { value: 1 }, uRays: { value: 1 },
    },
  });
}

function makeNebulaMaterial(rim, clump) {
  return shaderMaterial({
    vertex: SURFACE_VERT,
    fragment: NEBULA_FRAG,
    side: THREE.DoubleSide,
    uniforms: {
      uColorA: color(1, 1, 1), uColorB: color(1, 1, 1), uTime: { value: 0 }, uOpacity: { value: 0 },
      uSeed: { value: Math.random() * 20 }, uRim: { value: rim }, uClump: { value: clump }, uBase: { value: 0.1 },
    },
  });
}

function makeBeamMaterial(length, falloff, r, g, b) {
  return shaderMaterial({
    vertex: BEAM_VERT,
    fragment: BEAM_FRAG,
    side: THREE.DoubleSide,
    uniforms: { uColor: color(r, g, b), uOpacity: { value: 0 }, uH: { value: length }, uFalloff: { value: falloff } },
  });
}

function makeDiskMaterial({ inner, outer, colorIn, colorOut, spin, doppler, bright, streak }) {
  return shaderMaterial({
    vertex: DISK_VERT,
    fragment: DISK_FRAG,
    side: THREE.DoubleSide,
    uniforms: {
      uColorIn: { value: new THREE.Color(...colorIn) }, uColorOut: { value: new THREE.Color(...colorOut) },
      uTime: { value: 0 }, uIn: { value: inner }, uOut: { value: outer }, uSpin: { value: spin },
      uDoppler: { value: doppler }, uBright: { value: bright }, uOpacity: { value: 0 }, uStreak: { value: streak },
    },
  });
}

// A cone whose apex sits at the origin and whose base is `length` away along
// -Y (so a beam fades naturally from the star outward).
function makeBeamGeometry(baseRadius, length) {
  const geometry = new THREE.ConeGeometry(baseRadius, length, 32, 1, true);
  geometry.translate(0, -length / 2, 0);
  return geometry;
}

// Background: sparse bright stars in a range of colours and magnitudes, plus
// a dense, dim, tilted band standing in for the Milky Way.
function makeStarfield(pixelRatio) {
  const STAR_COLORS = [
    [0.62, 0.72, 1.0], [0.85, 0.9, 1.0], [1.0, 1.0, 1.0], [1.0, 0.92, 0.75], [1.0, 0.75, 0.5],
  ];
  const STAR_COLOR_WEIGHTS = [0.14, 0.24, 0.3, 0.2, 0.12];
  const pickColor = () => {
    let x = Math.random();
    for (let i = 0; i < STAR_COLORS.length; i++) {
      x -= STAR_COLOR_WEIGHTS[i];
      if (x <= 0) return STAR_COLORS[i];
    }
    return STAR_COLORS[2];
  };

  const FIELD = 1100;
  const BAND = 2400;
  const total = FIELD + BAND;
  const positions = new Float32Array(total * 3);
  const colors = new Float32Array(total * 3);
  const sizes = new Float32Array(total);
  const phases = new Float32Array(total);

  // Milky-Way plane normal, tilted so the band arcs across the frame.
  const bandNormal = new THREE.Vector3(0.35, 1.0, 0.25).normalize();
  const bandU = new THREE.Vector3().crossVectors(bandNormal, new THREE.Vector3(0, 0, 1)).normalize();
  const bandV = new THREE.Vector3().crossVectors(bandNormal, bandU).normalize();
  const dir = new THREE.Vector3();

  for (let i = 0; i < total; i++) {
    const inBand = i >= FIELD;
    if (inBand) {
      const angle = Math.random() * Math.PI * 2;
      const lift = (Math.random() + Math.random() + Math.random() - 1.5) * 0.28;
      dir.copy(bandU).multiplyScalar(Math.cos(angle)).addScaledVector(bandV, Math.sin(angle));
      dir.addScaledVector(bandNormal, lift).normalize();
    } else {
      dir.set(Math.random() * 2 - 1, Math.random() * 2 - 1, Math.random() * 2 - 1);
      if (dir.lengthSq() < 1e-4) dir.set(0, 1, 0);
      dir.normalize();
    }
    const radius = 70 + Math.random() * 30;
    positions.set([dir.x * radius, dir.y * radius, dir.z * radius], i * 3);

    if (inBand) {
      const tint = Math.random();
      const dim = 0.1 + Math.random() * 0.22;
      colors.set([(0.7 + tint * 0.3) * dim, (0.72 + (1 - tint) * 0.1) * dim, (1.0 - tint * 0.25) * dim], i * 3);
      sizes[i] = 1.1 + Math.random() * 0.7;
    } else {
      const [r, g, b] = pickColor();
      // Power-law magnitudes: many faint stars, a handful of bright ones.
      const bright = 0.35 + Math.pow(Math.random(), 3.0) * 1.9;
      colors.set([r * bright, g * bright, b * bright], i * 3);
      sizes[i] = 1.4 + Math.pow(Math.random(), 4.0) * 3.4;
    }
    phases[i] = Math.random();
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
  const material = shaderMaterial({
    vertex: STARFIELD_VERT,
    fragment: POINT_FRAG,
    uniforms: { uPixelRatio: { value: pixelRatio }, uTime: { value: 0 } },
  });
  return { points: new THREE.Points(geometry, material), geometry, material };
}

function makeEjecta(pixelRatio) {
  const COUNT = 3200;
  const positions = new Float32Array(COUNT * 3);
  const seeds = new Float32Array(COUNT);
  const dir = new THREE.Vector3();
  for (let i = 0; i < COUNT; i++) {
    dir.set(Math.random() * 2 - 1, Math.random() * 2 - 1, Math.random() * 2 - 1);
    if (dir.lengthSq() < 1e-4) dir.set(1, 0, 0);
    dir.normalize();
    // Speeds skewed slow-heavy, with a fast tail forming the leading edge.
    const speed = 0.12 + Math.pow(Math.random(), 1.6) * 0.88;
    positions.set([dir.x * speed, dir.y * speed, dir.z * speed], i * 3);
    seeds[i] = Math.random();
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
  const material = shaderMaterial({
    vertex: EJECTA_VERT,
    fragment: EJECTA_FRAG,
    uniforms: {
      uP: { value: 0 }, uMax: { value: 8 }, uPixelRatio: { value: pixelRatio }, uActive: { value: 0 },
    },
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  return { points, geometry, material };
}

// This app only ever mounts one <StarScene> at a time (the single-star
// detail view), so a module-level singleton for the live container/teardown
// is safe -- it keeps mountStarScene() a stable, hook-free ref callback (see
// note above) while still letting every StarScene() render push fresh prop
// values into the running Three.js scene.
let mountedContainer = null;
let teardown = null;

function mountStarScene(container) {
  if (container === null) {
    if (teardown) teardown();
    teardown = null;
    mountedContainer = null;
    return;
  }
  mountedContainer = container;
  // Matches SimState's initial values (state.py) -- covers the brief window
  // between this ref firing and StarScene()'s next render pushing real props.
  container._uniSimuLatest = container._uniSimuLatest || {
    radius: 0.01, color: "#552200", stage: "protostar", luminosity: 0.0001, progress: 0,
  };

  const disposables = [];
  const track = (resource) => {
    disposables.push(resource);
    return resource;
  };

  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: "high-performance" });
  } catch (err) {
    container.textContent = "This simulation needs WebGL, which isn't available in this browser.";
    container.style.cssText += ";display:flex;align-items:center;justify-content:center;color:#9c9284;text-align:center;padding:2em";
    teardown = () => {
      container.textContent = "";
    };
    return;
  }
  renderer.setPixelRatio(pixelRatio);
  renderer.setClearColor(SPACE_COLOR, 1);
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(SPACE_COLOR);
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  camera.position.set(0, 1.2, 6);

  // Bloom needs an HDR render target; MSAA on it keeps sphere edges smooth
  // since the composer bypasses the canvas's own antialiasing.
  const renderTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, renderTarget);
  composer.setPixelRatio(pixelRatio);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.55, 0.3, 0.88);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.minDistance = 2;
  controls.maxDistance = 26;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.35;

  // Auto-zoom: camera distance follows whatever the current stage needs
  // framed (the star, its nebula, its disk), so dramatic scale changes are
  // felt, not just read off a number. The user's own zoom is preserved as a
  // multiplier on top rather than snapped back after they let go.
  let userInteracting = false;
  let lastInteractionEnd = -Infinity;
  let userZoom = 1;
  let autoDistance = 6;
  controls.addEventListener("start", () => {
    userInteracting = true;
    controls.autoRotate = false;
  });
  controls.addEventListener("end", () => {
    userInteracting = false;
    lastInteractionEnd = performance.now();
    controls.autoRotate = true;
  });

  // ------------------------------------------------------------- scene ---
  const starfield = makeStarfield(pixelRatio);
  track(starfield.geometry);
  track(starfield.material);
  scene.add(starfield.points);

  // The star: self-luminous shader sphere + billboard corona.
  const starGeometry = track(new THREE.SphereGeometry(1, 64, 64));
  const starMaterial = track(makeStarMaterial());
  const star = new THREE.Mesh(starGeometry, starMaterial);
  scene.add(star);

  const quadGeometry = track(new THREE.PlaneGeometry(1, 1));
  const CORONA_EXTENT = 5; // quad half-size in star radii
  const coronaMaterial = track(makeCoronaMaterial(1 / CORONA_EXTENT));
  const corona = new THREE.Mesh(quadGeometry, coronaMaterial);
  scene.add(corona);

  // Supernova: blinding flash + shockwave shell + ejecta.
  const flashMaterial = track(makeCoronaMaterial(0));
  flashMaterial.uniforms.uRays.value = 0.9;
  const flash = new THREE.Mesh(quadGeometry, flashMaterial);
  flash.visible = false;
  scene.add(flash);

  const shellGeometry = track(new THREE.SphereGeometry(1, 64, 48));
  const shockMaterial = track(makeNebulaMaterial(3.5, 0.15));
  shockMaterial.uniforms.uBase.value = 0.015;
  shockMaterial.uniforms.uColorA.value.set(0.75, 0.88, 1.0);
  shockMaterial.uniforms.uColorB.value.set(1.0, 0.7, 0.4);
  const shock = new THREE.Mesh(shellGeometry, shockMaterial);
  shock.visible = false;
  scene.add(shock);

  const ejecta = makeEjecta(pixelRatio);
  track(ejecta.geometry);
  track(ejecta.material);
  scene.add(ejecta.points);

  // Lingering gas cloud: planetary nebula / supernova remnant.
  const nebulaMaterial = track(makeNebulaMaterial(2.2, 1.0));
  const nebula = new THREE.Mesh(shellGeometry, nebulaMaterial);
  nebula.visible = false;
  nebula.rotation.set(0.5, 0.3, 0.2);
  scene.add(nebula);

  // Pulsar: two beams on a magnetic axis tilted off the spin axis; spinning
  // the outer group sweeps them around like a lighthouse.
  const BEAM_LENGTH = 6;
  const beamGeometry = track(makeBeamGeometry(0.55, BEAM_LENGTH));
  const pulsarMaterial = track(makeBeamMaterial(BEAM_LENGTH, 1.6, 0.55, 0.7, 1.0));
  const pulsarSpin = new THREE.Group();
  const pulsarTilt = new THREE.Group();
  pulsarTilt.rotation.z = 0.6;
  const beamUp = new THREE.Mesh(beamGeometry, pulsarMaterial);
  beamUp.rotation.z = Math.PI;
  const beamDown = new THREE.Mesh(beamGeometry, pulsarMaterial);
  pulsarTilt.add(beamUp, beamDown);
  pulsarSpin.add(pulsarTilt);
  pulsarSpin.visible = false;
  scene.add(pulsarSpin);

  // Protostar: dusty accretion disk with bipolar jets.
  const dustDiskMaterial = track(makeDiskMaterial({
    inner: 1.0, outer: 4.4, colorIn: [1.0, 0.55, 0.2], colorOut: [0.32, 0.14, 0.07],
    spin: 1.6, doppler: 0.0, bright: 0.95, streak: 1.0,
  }));
  const diskGeometry = track(new THREE.RingGeometry(1.0, 4.4, 128, 4));
  const dustDisk = new THREE.Mesh(diskGeometry, dustDiskMaterial);
  dustDisk.rotation.x = Math.PI / 2 - 0.5;
  dustDisk.visible = false;
  scene.add(dustDisk);

  const JET_LENGTH = 3.2;
  const jetGeometry = track(makeBeamGeometry(0.15, JET_LENGTH));
  const jetMaterial = track(makeBeamMaterial(JET_LENGTH, 2.2, 0.95, 0.55, 0.3));
  const jets = new THREE.Group();
  const jetUp = new THREE.Mesh(jetGeometry, jetMaterial);
  jetUp.rotation.z = Math.PI;
  jets.add(jetUp, new THREE.Mesh(jetGeometry, jetMaterial));
  jets.rotation.z = 0.12;
  jets.visible = false;
  scene.add(jets);

  // Black hole: opaque horizon, hot Doppler-shifted disk, and the lens.
  const horizonGeometry = track(new THREE.SphereGeometry(1, 48, 48));
  const horizonMaterial = track(new THREE.MeshBasicMaterial({ color: 0x000000 }));
  const horizon = new THREE.Mesh(horizonGeometry, horizonMaterial);
  horizon.visible = false;
  scene.add(horizon);

  const blackHoleDiskMaterial = track(makeDiskMaterial({
    inner: 1.0, outer: 3.2, colorIn: [1.0, 0.85, 0.6], colorOut: [1.0, 0.3, 0.05],
    spin: 2.2, doppler: 0.55, bright: 0.85, streak: 1.0,
  }));
  const blackHoleDiskGeometry = track(new THREE.RingGeometry(1.0, 3.2, 128, 4));
  const blackHoleDisk = new THREE.Mesh(blackHoleDiskGeometry, blackHoleDiskMaterial);
  blackHoleDisk.rotation.x = Math.PI / 2 - 0.42;
  blackHoleDisk.visible = false;
  scene.add(blackHoleDisk);

  const lensMaterial = track(shaderMaterial({
    vertex: QUAD_VERT,
    fragment: LENS_FRAG,
    uniforms: { uTime: { value: 0 }, uOpacity: { value: 0 } },
  }));
  const lens = new THREE.Mesh(quadGeometry, lensMaterial);
  lens.visible = false;
  scene.add(lens);

  const timeUniforms = [
    starfield.material.uniforms.uTime, starMaterial.uniforms.uTime, coronaMaterial.uniforms.uTime,
    flashMaterial.uniforms.uTime, shockMaterial.uniforms.uTime, nebulaMaterial.uniforms.uTime,
    dustDiskMaterial.uniforms.uTime, blackHoleDiskMaterial.uniforms.uTime, lensMaterial.uniforms.uTime,
  ];

  // --------------------------------------------------------- live state ---
  const initial = container._uniSimuLatest;
  let displayRadius = visualScale(initial.radius);
  const displayColor = new THREE.Color(initial.color);
  let rotationSpeed = ROTATION_SPEED_BY_STAGE[initial.stage] ?? DEFAULT_ROTATION_SPEED;
  let previousStage = initial.stage;
  let elapsed = 0;

  const surface = { ...SURFACE_BY_STAGE[initial.stage] ?? SURFACE_BY_STAGE.main_sequence };
  let bodyIntensity = surface.intensity;
  let coronaIntensity = 1;
  let supernovaStartRadius = displayRadius;
  let dustOpacity = 0;
  let jetOpacity = 0;
  let pulsarOpacity = 0;
  let blackHoleOpacity = 0;
  const gas = {
    scale: 0.5,
    opacity: 0,
    colorA: PLANETARY_PALETTE[0].clone(),
    colorB: PLANETARY_PALETTE[1].clone(),
  };

  const tmpColor = new THREE.Color();
  const tmpVec = new THREE.Vector3();
  const tmpVec2 = new THREE.Vector3();
  const tmpQuat = new THREE.Quaternion();
  const worldUp = new THREE.Vector3(0, 1, 0);

  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    composer.setSize(w, h);
  }
  resize();
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);

  const onContextLost = (event) => event.preventDefault();
  renderer.domElement.addEventListener("webglcontextlost", onContextLost);

  function enterStage(to, targetRadius) {
    if (to === "supernova") supernovaStartRadius = displayRadius;
    // The star body has faded out by the end of the explosion, so a remnant
    // (or a fresh formation after Reset) appears at its size instead of
    // visibly shrinking/growing there.
    if (to === "neutron_star" || to === "black_hole" || to === "protostar") {
      displayRadius = targetRadius;
      bodyIntensity = 0;
    }
    if (to === "protostar" || to === "main_sequence") {
      gas.scale = 0.5;
      gas.opacity = 0;
    }
  }

  // ------------------------------------------------------- frame loop ----
  let rafId;
  let lastTime = performance.now();
  function animate(now) {
    rafId = requestAnimationFrame(animate);
    const delta = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;
    elapsed += delta;
    for (const u of timeUniforms) u.value = elapsed;

    const latest = container._uniSimuLatest;
    const stage = latest.stage;
    const p = clamp(latest.progress ?? 0, 0, 1);
    const isSupernova = stage === "supernova";
    const isBlackHole = stage === "black_hole";
    const isNeutronStar = stage === "neutron_star";
    const isRemnantStage = isNeutronStar || isBlackHole;

    // --- what the star's body should look like this stage ---------------
    const look = SURFACE_BY_STAGE[stage] ?? SURFACE_BY_STAGE.main_sequence;
    let targetRadius = visualScale(latest.radius);
    if (isNeutronStar) targetRadius = NEUTRON_STAR_RADIUS;
    if (isBlackHole) targetRadius = HORIZON_RADIUS;
    let targetIntensity = look.intensity;
    if (stage === "protostar") targetIntensity = 0.55 + 0.45 * p;

    if (stage !== previousStage) {
      enterStage(stage, targetRadius);
      previousStage = stage;
    }

    // Supernova: core collapse, bounce + flash, fireball that dissolves.
    let flashLevel = 0;
    if (isSupernova) {
      const collapseEnd = 0.05;
      if (p < collapseEnd) {
        const c = smoothstep(p, 0, collapseEnd);
        targetRadius = lerp(supernovaStartRadius, 0.45, c);
        targetIntensity = lerp(1, 1.4, c);
      } else {
        const burst = easeOutCubic((p - collapseEnd) / 0.45);
        targetRadius = 0.45 + 2.2 * burst;
        targetIntensity = 1.05 * (1 - smoothstep(p, 0.1, 0.6));
        flashLevel = p < 0.08 ? (p - collapseEnd) / (0.08 - collapseEnd) : Math.exp(-(p - 0.08) * 16);
      }
    }

    // The supernova drives its own size directly (it must be crisp, and
    // its timing is what the shockwave and flash are synced to); every other
    // stage eases toward its target.
    displayRadius = isSupernova ? targetRadius : damp(displayRadius, targetRadius, 2.5, delta);
    bodyIntensity = isSupernova ? targetIntensity : damp(bodyIntensity, targetIntensity, 3, delta);

    tmpColor.set(latest.color);
    displayColor.lerp(tmpColor, 1 - Math.exp(-(isSupernova ? 10 : 2.5) * delta));

    for (const key of ["cell", "contrast", "spots", "rays", "blotch"]) {
      surface[key] = damp(surface[key], look[key], 2, delta);
    }

    // Giants pulsate slowly, like a Mira variable.
    const pulsation = stage === "red_giant" || stage === "red_supergiant"
      ? 1 + 0.03 * Math.sin(elapsed * 1.7) + 0.012 * Math.sin(elapsed * 4.3)
      : 1;
    const shownRadius = displayRadius * pulsation;

    const targetRotation = ROTATION_SPEED_BY_STAGE[stage] ?? DEFAULT_ROTATION_SPEED;
    // Spin-up/down over ~1s rather than snapping, so a stage change (e.g.
    // collapsing into a fast-spinning neutron star) reads as acceleration.
    rotationSpeed = damp(rotationSpeed, targetRotation, 1.5, delta);
    star.rotation.y += delta * rotationSpeed;

    // --- the star body + corona -----------------------------------------
    star.visible = !isBlackHole && bodyIntensity > 0.01;
    star.scale.setScalar(Math.max(shownRadius, 0.001));
    starMaterial.uniforms.uColor.value.copy(displayColor).lerp(tmpColor.set(1, 1, 1), flashLevel * 0.5);
    starMaterial.uniforms.uIntensity.value = bodyIntensity;
    starMaterial.uniforms.uCellScale.value = surface.cell;
    starMaterial.uniforms.uContrast.value = surface.contrast;
    starMaterial.uniforms.uSpots.value = surface.spots;
    starMaterial.uniforms.uBlotch.value = surface.blotch;

    // Corona strength follows (log) luminosity, so a blazing supergiant
    // outshines a dim red dwarf, and pulses hard for a pulsar's sweep.
    const lumBoost = clamp(0.7 + 0.06 * Math.log10(Math.max(latest.luminosity ?? 1, 1e-4)), 0.45, 1.1);
    let coronaTarget = star.visible ? lumBoost * (isSupernova ? 0.3 + 0.7 * (1 - smoothstep(p, 0.15, 0.8)) : 1) : 0;
    if (isNeutronStar) {
      // Lighthouse strobe: brightest when a beam points at the camera.
      pulsarTilt.getWorldQuaternion(tmpQuat);
      tmpVec.copy(worldUp).applyQuaternion(tmpQuat);
      const align = Math.abs(tmpVec.dot(tmpVec2.copy(camera.position).normalize()));
      coronaTarget = 0.7 + 2.6 * Math.pow(align, 10);
    }
    coronaIntensity = isNeutronStar ? coronaTarget : damp(coronaIntensity, coronaTarget, 3, delta);
    corona.visible = coronaIntensity > 0.01;
    corona.quaternion.copy(camera.quaternion);
    corona.scale.setScalar(Math.max(shownRadius, 0.001) * CORONA_EXTENT * 2);
    coronaMaterial.uniforms.uColor.value.copy(starMaterial.uniforms.uColor.value);
    coronaMaterial.uniforms.uIntensity.value = coronaIntensity;
    coronaMaterial.uniforms.uRays.value = surface.rays;

    // --- supernova blast --------------------------------------------------
    const blastP = isSupernova ? clamp((p - 0.05) / 0.95, 0, 1) : 0;
    flash.visible = isSupernova && flashLevel > 0.005;
    if (flash.visible) {
      flash.quaternion.copy(camera.quaternion);
      flash.scale.setScalar(2 + flashLevel * 7);
      flashMaterial.uniforms.uColor.value.set(0.85, 0.92, 1.0);
      flashMaterial.uniforms.uIntensity.value = flashLevel * 0.8;
    }
    const shockProgress = isSupernova ? clamp((p - 0.05) / 0.6, 0, 1) : 0;
    shock.visible = isSupernova && p > 0.05 && shockProgress < 1;
    if (shock.visible) {
      shock.scale.setScalar(0.5 + 7.0 * easeOutCubic(shockProgress));
      shockMaterial.uniforms.uOpacity.value = 0.9 * Math.pow(1 - shockProgress, 1.5);
    }
    ejecta.material.uniforms.uP.value = blastP;
    ejecta.material.uniforms.uActive.value = isSupernova ? 1 : 0;
    ejecta.points.visible = isSupernova;

    // --- lingering nebula ---------------------------------------------------
    let nebulaScaleTarget = gas.scale;
    let nebulaOpacityTarget = 0;
    let palette = null;
    if (stage === "planetary_nebula") {
      nebulaScaleTarget = lerp(0.8, 5.0, easeOutCubic(p));
      nebulaOpacityTarget = 1.0 * smoothstep(p, 0.0, 0.2);
      palette = PLANETARY_PALETTE;
    } else if (stage === "white_dwarf") {
      nebulaScaleTarget = Math.min(gas.scale + delta * 0.12, 5.5);
      nebulaOpacityTarget = 0.42;
      palette = PLANETARY_PALETTE;
    } else if (isSupernova) {
      nebulaScaleTarget = lerp(0.5, 6.5, easeOutCubic(clamp((p - 0.05) / 0.9, 0, 1)));
      nebulaOpacityTarget = 0.9 * smoothstep(p, 0.15, 0.55);
      palette = SUPERNOVA_PALETTE;
    } else if (isRemnantStage) {
      nebulaScaleTarget = Math.min(gas.scale + delta * 0.1, 5.5);
      nebulaOpacityTarget = 0.4;
      palette = SUPERNOVA_PALETTE;
    }
    if (palette) {
      gas.colorA.lerp(palette[0], 1 - Math.exp(-3 * delta));
      gas.colorB.lerp(palette[1], 1 - Math.exp(-3 * delta));
    }
    gas.scale = isSupernova || stage === "planetary_nebula" ? damp(gas.scale, nebulaScaleTarget, 6, delta) : nebulaScaleTarget;
    gas.opacity = damp(gas.opacity, nebulaOpacityTarget, nebulaOpacityTarget > gas.opacity ? 1.6 : 4, delta);
    nebula.visible = gas.opacity > 0.01;
    nebula.scale.set(gas.scale, gas.scale * 0.86, gas.scale * 1.08);
    nebula.rotation.y += delta * 0.03;
    nebulaMaterial.uniforms.uOpacity.value = gas.opacity;
    nebulaMaterial.uniforms.uColorA.value.copy(gas.colorA);
    nebulaMaterial.uniforms.uColorB.value.copy(gas.colorB);

    // --- protostar disk + jets, pulsar beams -----------------------------
    dustOpacity = damp(dustOpacity, stage === "protostar" ? 1 - smoothstep(p, 0.55, 1.0) : 0, 2, delta);
    dustDisk.visible = dustOpacity > 0.01;
    dustDisk.scale.setScalar(Math.max(displayRadius, 0.2) * 1.6);
    dustDiskMaterial.uniforms.uOpacity.value = dustOpacity;

    jetOpacity = damp(jetOpacity, stage === "protostar" ? 0.5 * (1 - smoothstep(p, 0.6, 1.0)) : 0, 2, delta);
    jets.visible = jetOpacity > 0.01;
    jets.scale.setScalar(Math.max(displayRadius, 0.3) / 0.43);
    jetMaterial.uniforms.uOpacity.value = jetOpacity;

    pulsarOpacity = damp(pulsarOpacity, isNeutronStar ? 1 : 0, 1.5, delta);
    pulsarSpin.visible = pulsarOpacity > 0.01;
    pulsarSpin.rotation.y = star.rotation.y;
    pulsarMaterial.uniforms.uOpacity.value = pulsarOpacity * 1.15;

    // --- black hole ---------------------------------------------------------
    blackHoleOpacity = damp(blackHoleOpacity, isBlackHole ? 1 : 0, 1.2, delta);
    horizon.visible = isBlackHole;
    horizon.scale.setScalar(displayRadius);
    blackHoleDisk.visible = blackHoleOpacity > 0.01;
    blackHoleDisk.scale.setScalar(displayRadius * 1.7);
    blackHoleDiskMaterial.uniforms.uOpacity.value = blackHoleOpacity;
    lens.visible = blackHoleOpacity > 0.01;
    lens.quaternion.copy(camera.quaternion);
    lens.scale.setScalar(displayRadius * 6);
    lensMaterial.uniforms.uOpacity.value = blackHoleOpacity;

    // --- bloom: the flash briefly overexposes everything ------------------
    bloom.strength = 0.55 + flashLevel * 0.6 + (isBlackHole ? 0.2 : 0);

    // --- camera ---------------------------------------------------------------
    let frame = displayRadius;
    // A nebula sets the framing only while it's the subject; around a
    // pulsar or black hole it's backdrop, and the compact object matters.
    if (gas.opacity > 0.05 && !isRemnantStage) frame = Math.max(frame, gas.scale * 0.55);
    if (pulsarOpacity > 0.05) frame = Math.max(frame, 2.6);
    if (blackHoleOpacity > 0.05) frame = Math.max(frame, 2.5);
    if (dustOpacity > 0.05) frame = Math.max(frame, displayRadius * 2.6);
    if (isSupernova) frame = Math.max(frame, 1.5 + 3.4 * easeOutCubic(clamp((p - 0.05) / 0.6, 0, 1)));
    autoDistance = clamp(3 + frame * 2.3, 2.6, 22);

    const currentDistance = camera.position.distanceTo(controls.target);
    if (userInteracting || performance.now() - lastInteractionEnd < 700) {
      // Whatever zoom the user just chose becomes the new baseline.
      userZoom = clamp(currentDistance / autoDistance, 0.4, 3.0);
    } else {
      const wanted = clamp(autoDistance * userZoom, controls.minDistance, controls.maxDistance);
      const newDistance = damp(currentDistance, wanted, 1.0, delta);
      tmpVec.subVectors(camera.position, controls.target).setLength(newDistance);
      camera.position.copy(controls.target).add(tmpVec);
    }

    controls.update();

    // Camera shake at the moment of the blast; applied for the render only
    // so OrbitControls never sees (and accumulates) the offset.
    const shake = isSupernova ? 0.12 * flashLevel : 0;
    const shakeX = (Math.random() - 0.5) * shake;
    const shakeY = (Math.random() - 0.5) * shake;
    camera.position.x += shakeX;
    camera.position.y += shakeY;
    composer.render(delta);
    camera.position.x -= shakeX;
    camera.position.y -= shakeY;
  }
  rafId = requestAnimationFrame(animate);

  teardown = () => {
    cancelAnimationFrame(rafId);
    resizeObserver.disconnect();
    renderer.domElement.removeEventListener("webglcontextlost", onContextLost);
    controls.dispose();
    for (const resource of disposables) resource.dispose();
    renderTarget.dispose();
    composer.dispose();
    renderer.dispose();
    if (renderer.domElement.parentNode === container) {
      container.removeChild(renderer.domElement);
    }
  };
}

export function StarScene({ radius, color, stage, luminosity, progress }) {
  if (mountedContainer) {
    mountedContainer._uniSimuLatest = { radius, color, stage, luminosity, progress };
  }
  return <div ref={mountStarScene} style={{ width: "100%", height: "100%" }} />;
}
