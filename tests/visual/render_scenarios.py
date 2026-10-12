"""Render the 3D scene directly -- no Reflex server, no React -- with props
computed by the real physics, and report every console error (three.js logs
GLSL compile/link failures there) plus one screenshot per scenario.

Not a pytest test. Run it from the repo root (the frontend must have been
built once, so .web/node_modules/three exists):

    venv/Scripts/python tests/visual/render_scenarios.py [--out DIR] [--only NAME ...]

It copies assets/star_scene.jsx into a temp folder (JSX return line removed,
`mountStarScene` exported, three.js imported via an import map), serves that
folder, .web/node_modules and assets/starfield.bin from a local thread, and
loads the module in headless Chromium (SwiftShader). Uses about 300-400 MB,
far less than `reflex run` plus a browser.
"""

import argparse
import functools
import http.server
import json
import math
import sys
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from unisimu.physics import death, relativity, stellar, surface  # noqa: E402
from unisimu.physics.blackbody import blackbody_display_color  # noqa: E402

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000}#c{width:960px;height:600px}</style>
<script type="importmap">{"imports":{"three":"/nm/three/build/three.module.js"}}</script></head>
<body><div id="c"></div><script type="module">
import { mountStarScene } from "/scene.mjs";
const c = document.getElementById("c");
window.__setProps = (p) => { c._uniSimuLatest = p; };
c._uniSimuLatest = { radius: 1, color: "#fff4ea", stage: "main_sequence", luminosity: 1, progress: 0.5 };
mountStarScene(c);
window.__ready = true;
</script></body></html>"""

BH_PARAMS = [
    relativity.HORIZON_RADIUS_M,
    relativity.ISCO_RADIUS_M,
    relativity.DISK_OUTER_RADIUS_M,
    relativity.DISK_PEAK_TEMPERATURE_K,
    blackbody_display_color(relativity.DISK_PEAK_TEMPERATURE_K)[1],
]


def scene_props(mass: float, age: float, mode: str, **extra) -> dict:
    """The props viewport.py would send for this star, from the same physics."""
    s = stellar.evolve(mass, age)
    color, lum = blackbody_display_color(s.temperature_k)
    photosphere = s.stage not in stellar.TERMINAL_STAGES and s.temperature_k > 0
    logg = surface.surface_gravity_cgs(mass, max(s.radius_rsun, 1e-9))
    visibility = surface.granulation_visibility(s.temperature_k) if photosphere else 0.0
    props = dict(
        radius=s.radius_rsun, color=s.color_hex, stage=s.stage, luminosity=s.luminosity_lsun,
        progress=s.stage_progress, surfaceColor=list(color), surfaceLuminance=lum,
        renderMode=mode, exposureMode="auto",
        limbDarkening=list(surface.limb_darkening(s.temperature_k, logg)),
        granulationCells=surface.granulation_scale(s.temperature_k, mass, s.radius_rsun) if photosphere else 0.0,
        granulationAmplitude=surface.GRANULATION_TEMPERATURE_CONTRAST * visibility,
        temperatureSensitivity=list(surface.temperature_sensitivity(s.temperature_k)),
        spotContrast=list(surface.spot_contrast(s.temperature_k)),
        pulsationPeriodDays=(
            surface.pulsation_period_days(mass, s.radius_rsun) if s.stage in ("red_giant", "red_supergiant") else 0.0
        ),
        glare=True, coronagraph=False, convection=visibility,
        nebulaColor=list(death.emission_line_color()), illustrativeEffects=False,
        bhParams=BH_PARAMS, bhColorTable=relativity.blackbody_color_table(), bhDisk=False,
    )
    props.update(extra)
    return props


def _at(mass: float, phase: int, frac: float) -> float:
    start, end, _ = stellar.phase_schedule(mass)[phase]
    return start + (end - start) * frac


def _remnant(mass: float) -> float:
    return stellar.phase_schedule(mass)[-1][1] + 1.0


SCENARIOS = {
    "sun_ms_stylized": lambda: scene_props(1.0, _at(1.0, 1, 0.5), "stylized"),
    "sun_ms_physical": lambda: scene_props(1.0, _at(1.0, 1, 0.5), "physical"),
    "betelgeuse_rsg_physical": lambda: scene_props(16.5, _at(16.5, 2, 0.97), "physical"),
    "betelgeuse_rsg_coronagraph": lambda: scene_props(16.5, _at(16.5, 2, 0.97), "physical", coronagraph=True),
    "rigel_ms_physical": lambda: scene_props(23.0, _at(23.0, 1, 0.5), "physical"),
    "supernova_day50_physical": lambda: scene_props(16.5, _at(16.5, 3, 50 / 400), "physical"),
    "sun_pn_physical": lambda: scene_props(1.0, _at(1.0, 3, 0.5), "physical"),
    "neutron_star_physical": lambda: scene_props(16.5, _remnant(16.5), "physical"),
    "black_hole_stylized": lambda: scene_props(23.0, _remnant(23.0), "stylized"),
    "black_hole_physical": lambda: scene_props(23.0, _remnant(23.0), "physical"),
    "black_hole_physical_disk": lambda: scene_props(23.0, _remnant(23.0), "physical", bhDisk=True),
}


def build_site(folder: Path) -> None:
    src = (REPO / "assets" / "star_scene.jsx").read_text(encoding="utf-8")
    src = src.replace('return <div ref={mountStarScene} style={{ width: "100%", height: "100%" }} />;', "return null;")
    src = src.replace('from "three";', 'from "/nm/three/build/three.module.js";')
    src = src.replace('from "three/examples/jsm/', 'from "/nm/three/examples/jsm/')
    (folder / "scene.mjs").write_text(src + "\nexport { mountStarScene };\n", encoding="utf-8")
    (folder / "index.html").write_text(PAGE, encoding="utf-8")


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript"}

    def __init__(self, *args, site: Path, **kwargs):
        self.site = site
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        path = path.split("?")[0]
        if path.startswith("/nm/"):
            return str(REPO / ".web" / "node_modules" / path[4:])
        if path == "/starfield.bin":
            return str(REPO / "assets" / "starfield.bin")
        return str(self.site / path.lstrip("/"))

    def log_message(self, *args):
        pass


def shadow_check(png: Path, camera_r_over_m: float) -> str:
    """Measured shadow radius (dark run through the image centre) vs Synge."""
    try:
        from PIL import Image
    except ImportError:
        return "shadow check skipped (Pillow not installed)"
    im = Image.open(png).convert("L")
    w, h = im.size
    px = im.load()
    row = [x for x in range(w) if px[x, h // 2] < 6]
    col = [y for y in range(h) if px[w // 2, y] < 6]
    measured = ((row[-1] - row[0] + 1) + (col[-1] - col[0] + 1)) / 4
    focal = (h / 2) / math.tan(math.radians(25))  # camera FOV 50 deg
    predicted = focal * math.tan(relativity.shadow_angular_radius(camera_r_over_m))
    return f"shadow radius {measured:.1f} px vs Synge {predicted:.1f} px"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="tests/visual/scenarios")
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = args.only or list(SCENARIOS)
    report = {}
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)
        build_site(site)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Handler, site=site))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/index.html?unisimuSeed=1&unisimuFreeze=5"
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
            page = browser.new_page(viewport={"width": 1000, "height": 640})
            log: list[str] = []
            page.on("console", lambda m: log.append(f"{m.type}: {m.text[:400]}") if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: log.append(f"pageerror: {e}"))
            page.goto(url)
            page.wait_for_function("window.__ready === true", timeout=60000)
            page.wait_for_timeout(4000)
            for name in names:
                start = len(log)
                page.evaluate("p => window.__setProps(p)", SCENARIOS[name]())
                page.wait_for_timeout(7000)
                png = out / f"{name}.png"
                page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": 960, "height": 600}, timeout=180000)
                entry = {"console": log[start:]}
                if name == "black_hole_physical":
                    # default framing: autoDistance = 3 + 2.5 * 2.3 scene units, M = 0.6 / 2
                    entry["shadow"] = shadow_check(png, (3 + 2.5 * 2.3) / 0.3)
                report[name] = entry
                print(f"{name}: {len(entry['console'])} console errors {entry.get('shadow', '')}", flush=True)
            browser.close()
        server.shutdown()
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
