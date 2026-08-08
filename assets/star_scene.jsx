import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

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

// Physical radius spans ~5 orders of magnitude (neutron star to red
// supergiant), which would make most stages invisible or off-screen at a
// 1:1 scale. Map to a bounded visual scale with a log curve instead.
function visualScale(radiusRsun) {
  return THREE.MathUtils.clamp(Math.log1p(Math.max(radiusRsun, 0)) * 0.6 + 0.3, 0.15, 3.5);
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
  supernova: 0.6,
  planetary_nebula: 0.06,
  white_dwarf: 0.3,
  neutron_star: 6.0,
  black_hole: 0.02,
};
const DEFAULT_ROTATION_SPEED = 0.1;

const ACCRETION_DISK_STAGES = new Set(["neutron_star", "black_hole"]);

function createGlowTexture() {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(
    size / 2, size / 2, 0,
    size / 2, size / 2, size / 2,
  );
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.35, "rgba(255,255,255,0.5)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(canvas);
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
    radius: 0.01, color: "#552200", stage: "protostar", luminosity: 0.0001,
  };

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  camera.position.set(0, 0, 6);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = false;
  controls.minDistance = 2;
  controls.maxDistance = 20;

  // Auto-zoom: camera distance follows the star's (visual) radius, so
  // dramatic scale changes -- red giant expansion, supernova collapse --
  // are felt, not just read off a number. Paused while the user is
  // actively dragging so it doesn't fight manual control.
  let userInteracting = false;
  let resumeTimeout = null;
  controls.addEventListener("start", () => {
    userInteracting = true;
    if (resumeTimeout) clearTimeout(resumeTimeout);
  });
  controls.addEventListener("end", () => {
    resumeTimeout = setTimeout(() => {
      userInteracting = false;
    }, 2500);
  });

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const pointLight = new THREE.PointLight(0xffffff, 1.2);
  pointLight.position.set(5, 5, 5);
  scene.add(pointLight);

  // A plain colored sphere in an empty void gives no visual reference for
  // camera orbit -- it looks identical from every angle, so dragging to
  // rotate reads as "broken" even though the camera is moving. A static
  // starfield provides parallax cues that make orbiting visible, and
  // doubles as ambience.
  const STAR_COUNT = 800;
  const starPositions = new Float32Array(STAR_COUNT * 3);
  for (let i = 0; i < STAR_COUNT; i++) {
    const radius = 40 + Math.random() * 60;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(THREE.MathUtils.randFloatSpread(2));
    starPositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    starPositions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    starPositions[i * 3 + 2] = radius * Math.cos(phi);
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  const starMaterial = new THREE.PointsMaterial({
    color: 0xffffff,
    size: 0.12,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.8,
  });
  const starfield = new THREE.Points(starGeometry, starMaterial);
  scene.add(starfield);

  const geometry = new THREE.SphereGeometry(1, 48, 48);
  const material = new THREE.MeshStandardMaterial({ toneMapped: false });
  const sphere = new THREE.Mesh(geometry, material);
  scene.add(sphere);

  // Corona/glow halo: a camera-facing sprite with a soft radial-gradient
  // texture, additively blended so it reads as light rather than a flat
  // disc. Cheap "fake glow" technique, no post-processing bloom pass
  // needed.
  const glowTexture = createGlowTexture();
  const glowMaterial = new THREE.SpriteMaterial({
    map: glowTexture,
    color: 0xffffff,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const glowSprite = new THREE.Sprite(glowMaterial);
  scene.add(glowSprite);

  // Accretion disk: only meaningful (and only shown) once the star has
  // collapsed to a neutron star or black hole.
  const diskGeometry = new THREE.RingGeometry(1.6, 3.4, 64);
  const diskMaterial = new THREE.MeshBasicMaterial({
    color: 0xffaa55,
    transparent: true,
    opacity: 0,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const disk = new THREE.Mesh(diskGeometry, diskMaterial);
  disk.rotation.x = Math.PI / 2.3;
  scene.add(disk);

  let displayRadius = visualScale(container._uniSimuLatest.radius);
  const displayColor = new THREE.Color(container._uniSimuLatest.color);
  let rotationSpeed = ROTATION_SPEED_BY_STAGE[container._uniSimuLatest.stage] ?? DEFAULT_ROTATION_SPEED;
  let diskOpacity = ACCRETION_DISK_STAGES.has(container._uniSimuLatest.stage) ? 1 : 0;
  sphere.scale.setScalar(displayRadius);
  material.color.copy(displayColor);

  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  resize();
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);

  let rafId;
  let lastTime = performance.now();
  function animate(now) {
    rafId = requestAnimationFrame(animate);
    const delta = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;

    const latest = container._uniSimuLatest;
    const targetRadius = visualScale(latest.radius);
    const targetColor = new THREE.Color(latest.color);
    const k = Math.min(1, delta * 2.5);
    displayRadius = THREE.MathUtils.lerp(displayRadius, targetRadius, k);
    displayColor.lerp(targetColor, k);

    sphere.scale.setScalar(displayRadius);
    material.color.copy(displayColor);

    const targetRotationSpeed = ROTATION_SPEED_BY_STAGE[latest.stage] ?? DEFAULT_ROTATION_SPEED;
    // Spin-up/down over ~1s rather than snapping, so a stage change (e.g.
    // collapsing into a fast-spinning neutron star) reads as acceleration.
    rotationSpeed = THREE.MathUtils.lerp(rotationSpeed, targetRotationSpeed, Math.min(1, delta * 1.0));
    sphere.rotation.y += delta * rotationSpeed;

    // Glow scales with both size and (log-compressed) luminosity, so a
    // small-but-blazing white dwarf still reads as bright.
    const luminosityBoost = Math.log1p(Math.max(latest.luminosity ?? 0, 0)) * 0.5;
    const glowScale = THREE.MathUtils.clamp(displayRadius * (2.2 + luminosityBoost), 1.0, 14);
    glowSprite.scale.setScalar(glowScale);
    glowSprite.material.color.copy(displayColor);

    const targetDiskOpacity = ACCRETION_DISK_STAGES.has(latest.stage) ? 0.85 : 0;
    diskOpacity = THREE.MathUtils.lerp(diskOpacity, targetDiskOpacity, Math.min(1, delta * 2.0));
    disk.material.opacity = diskOpacity;
    const diskScale = Math.max(displayRadius, 0.5);
    disk.scale.setScalar(diskScale);
    disk.rotation.z += delta * 1.5;

    if (!userInteracting) {
      const targetDistance = THREE.MathUtils.clamp(
        4 + displayRadius * 2,
        controls.minDistance,
        controls.maxDistance,
      );
      const offset = new THREE.Vector3().subVectors(camera.position, controls.target);
      const spherical = new THREE.Spherical().setFromVector3(offset);
      // Slower than the color/radius lerp (k=2.5 above) -- this is a
      // deliberate, readable camera move, not a snap.
      const kZoom = Math.min(1, delta * 1.0);
      spherical.radius = THREE.MathUtils.lerp(spherical.radius, targetDistance, kZoom);
      offset.setFromSpherical(spherical);
      camera.position.copy(controls.target).add(offset);
    }

    controls.update();
    renderer.render(scene, camera);
  }
  rafId = requestAnimationFrame(animate);

  teardown = () => {
    cancelAnimationFrame(rafId);
    if (resumeTimeout) clearTimeout(resumeTimeout);
    resizeObserver.disconnect();
    controls.dispose();
    geometry.dispose();
    material.dispose();
    glowTexture.dispose();
    glowMaterial.dispose();
    diskGeometry.dispose();
    diskMaterial.dispose();
    starGeometry.dispose();
    starMaterial.dispose();
    renderer.dispose();
    if (renderer.domElement.parentNode === container) {
      container.removeChild(renderer.domElement);
    }
  };
}

export function StarScene({ radius, color, stage, luminosity }) {
  if (mountedContainer) {
    mountedContainer._uniSimuLatest = { radius, color, stage, luminosity };
  }
  return <div ref={mountStarScene} style={{ width: "100%", height: "100%" }} />;
}
