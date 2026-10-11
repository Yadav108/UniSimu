"""Capture a visual baseline of every preset, one viewport screenshot per stage.

Not a pytest test (pytest only collects test_*.py). Run it by hand while
`reflex run` is serving on localhost:3000:

    venv/Scripts/python tests/visual/capture_baseline.py [--out tests/visual/baseline]

For each preset it opens the shelf, clicks the preset card, plays at 1x, and
screenshots the <canvas> the first time each stage's progress bar reaches
50 % (terminal stages: 3 s after they are entered). It pauses the sim around
each screenshot, so the recorded progress is where the frame really is.

Do not edit any file in the repo while this runs: a file change makes
`reflex run` hot-reload, re-run npm install and, on this OneDrive folder,
fail with EBUSY and kill the backend (issue #14). A second pass at 16x only
records the stage order reached and console errors. Everything it saw is
written to report.json next to the images.

Headless Chromium renders WebGL through SwiftShader (CPU), so the frame times
in the report measure the software rasteriser, not a real GPU. The scene also
animates on wall-clock time (auto-rotate, twinkle, noise drift), so two runs
are never pixel-identical: compare with a tolerance.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unisimu.copy import STAGE_LABELS  # noqa: E402
from unisimu.physics.stellar import TERMINAL_STAGES, stage_track  # noqa: E402
from unisimu.presets import PRESETS  # noqa: E402

URL = "http://localhost:3000/"
SCENE_LOAD_MS = 8000  # the star scene is lazy-loaded; first frame takes a few seconds
POLL_S = 0.1
STAGE_TIMEOUT_S = 90.0

LABEL_TO_STAGE = {label.lower(): stage for stage, label in STAGE_LABELS.items()}

# First leaf element whose text is a stage label is the status-bar badge.
READ_STATUS_JS = """(labels) => {
  const leaves = Array.from(document.querySelectorAll('div,span,p'))
    .filter(e => e.children.length === 0);
  const badge = leaves.find(e => labels.includes(e.textContent.trim().toLowerCase()));
  const bar = document.querySelector('[role=progressbar]');
  return {
    label: badge ? badge.textContent.trim().toLowerCase() : null,
    progress: bar ? Number(bar.getAttribute('aria-valuenow')) : null,
  };
}"""

# Mean/p95 interval between animation frames over `ms` milliseconds.
FRAME_TIME_JS = """(ms) => new Promise(resolve => {
  const t = []; const start = performance.now();
  function step(now) { t.push(now); if (now - start < ms) requestAnimationFrame(step);
    else { const d = t.slice(1).map((v, i) => v - t[i]).sort((a, b) => a - b);
      resolve({frames: d.length, mean_ms: d.reduce((a, b) => a + b, 0) / d.length,
               p95_ms: d[Math.floor(d.length * 0.95)]}); } }
  requestAnimationFrame(step);
})"""


def open_preset(page, preset, speed: str) -> None:
    page.goto(URL, wait_until="networkidle")
    # the session remembers the detail view across reloads; go back to the shelf first
    back = page.get_by_role("button", name="← Shelf")
    if back.count():
        back.click()
    page.get_by_text(preset.name, exact=True).click()
    # the first load after a server start can take a while (dev-server bundling)
    page.locator("canvas").wait_for(state="attached", timeout=120000)
    page.wait_for_timeout(SCENE_LOAD_MS)
    page.get_by_role("radio", name=f"{speed}×").click()
    page.get_by_role("button", name="Play").click()


def read_status(page) -> tuple[str | None, int | None]:
    status = page.evaluate(READ_STATUS_JS, list(LABEL_TO_STAGE))
    return LABEL_TO_STAGE.get(status["label"]), status["progress"]


def capture_preset(page, preset, out_dir: Path) -> dict:
    track = stage_track(preset.mass_msun)
    shots: dict[str, dict] = {}
    seen: list[str] = []
    frame_times = None
    open_preset(page, preset, "1")
    entered_at: dict[str, float] = {}
    deadline = time.monotonic() + STAGE_TIMEOUT_S * len(track)
    while time.monotonic() < deadline:
        stage, progress = read_status(page)
        if stage and stage not in seen:
            seen.append(stage)
            entered_at[stage] = time.monotonic()
            print(f"  {preset.key}: entered {stage}", flush=True)
        terminal_ready = (
            stage in TERMINAL_STAGES and time.monotonic() - entered_at.get(stage, 0) > 3.0
        )
        if stage and stage not in shots and ((progress or 0) >= 50 or terminal_ready):
            index = track.index(stage) if stage in track else 99
            path = out_dir / f"{index:02d}_{stage}.png"
            # Pause the sim clock while capturing: under a software renderer a
            # screenshot takes seconds, long enough to skip a whole short stage.
            terminal = stage in TERMINAL_STAGES
            if not terminal:
                page.get_by_role("button", name="Pause").click()
                stage, progress = read_status(page)
            page.locator("canvas").screenshot(path=str(path))
            shots[stage] = {"file": path.name, "progress_pct": progress}
            if stage == "main_sequence" and frame_times is None:
                frame_times = page.evaluate(FRAME_TIME_JS, 3000)
            if not terminal:
                page.get_by_role("button", name="Play").click()
        if stage in TERMINAL_STAGES and stage in shots:
            break
        time.sleep(POLL_S)
    return {
        "expected_track": list(track),
        "stages_seen_1x": seen,
        "screenshots": shots,
        "missing": [s for s in track if s not in shots],
        "frame_time_main_sequence_1x": frame_times,
    }


def stage_order_16x(page, preset) -> list[str]:
    open_preset(page, preset, "16")
    seen: list[str] = []
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        stage, _ = read_status(page)
        if stage and stage not in seen:
            seen.append(stage)
        if stage in TERMINAL_STAGES:
            break
        time.sleep(POLL_S / 2)
    return seen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="tests/visual/baseline")
    args = parser.parse_args()
    out_root = Path(args.out)
    report: dict = {"url": URL, "renderer": "headless chromium + SwiftShader", "presets": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for preset in PRESETS:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            console: list[str] = []
            page.on(
                "console",
                lambda m: console.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None,
            )
            page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
            out_dir = out_root / preset.key
            out_dir.mkdir(parents=True, exist_ok=True)
            entry = {}
            try:
                entry = capture_preset(page, preset, out_dir)
                entry["stages_seen_16x"] = stage_order_16x(page, preset)
            except Exception as exc:  # keep going; record what broke
                entry["error"] = repr(exc)
            entry["console"] = console
            report["presets"][preset.key] = entry
            print(f"{preset.key}: shots={list(entry.get('screenshots', {}))} "
                  f"missing={entry.get('missing')} error={entry.get('error')} "
                  f"console={len(console)}", flush=True)
            page.close()
        browser.close()
    (out_root / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
