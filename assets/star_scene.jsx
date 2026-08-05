import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

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

export function StarScene({ radius, color }) {
  const containerRef = useRef(null);
  // The render loop reads live prop values through this ref rather than
  // restarting the whole Three.js scene (renderer/camera/controls) on every
  // Python-driven prop update.
  const latestRef = useRef({ radius, color });
  latestRef.current = { radius, color };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

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

    const geometry = new THREE.SphereGeometry(1, 48, 48);
    const material = new THREE.MeshStandardMaterial({ toneMapped: false });
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    let displayRadius = visualScale(latestRef.current.radius);
    const displayColor = new THREE.Color(latestRef.current.color);
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

      const targetRadius = visualScale(latestRef.current.radius);
      const targetColor = new THREE.Color(latestRef.current.color);
      const k = Math.min(1, delta * 2.5);
      displayRadius = THREE.MathUtils.lerp(displayRadius, targetRadius, k);
      displayColor.lerp(targetColor, k);

      sphere.scale.setScalar(displayRadius);
      material.color.copy(displayColor);
      sphere.rotation.y += delta * 0.1;

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

    return () => {
      cancelAnimationFrame(rafId);
      if (resumeTimeout) clearTimeout(resumeTimeout);
      resizeObserver.disconnect();
      controls.dispose();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
