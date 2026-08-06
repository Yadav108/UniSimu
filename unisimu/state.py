"""Reactive state for UniSimu: user controls plus the server-side
simulation loop that streams a star's evolving properties to the client."""

import asyncio

import reflex as rx
from reflex.event import KeyInputInfo

from unisimu.copy import STAGE_CAPTIONS
from unisimu.physics.stellar import TERMINAL_STAGES, StellarSnapshot, evolve, stage_track

TICK_HZ = 20
SIM_YEARS_PER_SECOND_AT_1X = 2_000_000
MIN_MASS_MSUN = 0.1
MAX_MASS_MSUN = 150.0
SPEED_OPTIONS = ["0.25", "1", "4", "16"]


class SimState(rx.State):
    # navigation: "shelf" (browse preset stars) or "detail" (single-star sim)
    view: str = "shelf"

    # user-controlled
    mass_msun: float = 1.0
    speed_multiplier: float = 1.0
    playing: bool = False

    # simulation clock (authoritative)
    age_years: float = 0.0

    # display vars, set atomically once per tick from evolve()
    stage: str = "protostar"
    radius_rsun: float = 0.01
    temperature_k: float = 2000.0
    luminosity_lsun: float = 0.0001
    color_hex: str = "#552200"
    stage_progress: float = 0.0
    event_flag: str = ""

    # backend-only loop guards, never sent to the client
    _run_id: int = 0
    _n_loops_running: int = 0

    @rx.event
    def set_mass(self, value: list[float]):
        self.mass_msun = max(MIN_MASS_MSUN, min(MAX_MASS_MSUN, float(value[0])))
        return SimState.reset_simulation

    @rx.event
    def select_preset(self, mass: float):
        self.mass_msun = mass
        self.view = "detail"
        return SimState.reset_simulation

    @rx.event
    def back_to_shelf(self):
        # tick_loop's existing `if not self.playing: return` stops it cleanly.
        self.playing = False
        self.view = "shelf"

    @rx.event
    def set_speed(self, value: str | list[str]):
        chosen = value[0] if isinstance(value, list) else value
        self.speed_multiplier = float(chosen)

    @rx.event
    def play(self):
        if self.playing or self.stage in TERMINAL_STAGES:
            return
        self.playing = True
        return SimState.tick_loop

    @rx.event
    def pause(self):
        self.playing = False

    @rx.event
    def toggle_play_pause(self):
        if self.playing:
            self.playing = False
            return None
        return SimState.play

    @rx.event
    def handle_key(self, key: str, modifiers: KeyInputInfo):
        # Ignore shortcuts while the user is typing into an input/textarea.
        if modifiers.get("alt_key") or modifiers.get("ctrl_key") or modifiers.get("meta_key"):
            return
        if key == " ":
            return SimState.toggle_play_pause
        if key.lower() == "r":
            return SimState.reset_simulation
        return None

    @rx.event
    def reset_simulation(self):
        self.playing = False
        self.age_years = 0.0
        self._run_id += 1
        self._apply_snapshot(evolve(self.mass_msun, 0.0))
        self.event_flag = ""

    def _apply_snapshot(self, snap: StellarSnapshot) -> None:
        self.stage = snap.stage
        self.radius_rsun = snap.radius_rsun
        self.temperature_k = snap.temperature_k
        self.luminosity_lsun = snap.luminosity_lsun
        self.color_hex = snap.color_hex
        self.stage_progress = snap.stage_progress

    @rx.event(background=True)
    async def tick_loop(self):
        async with self:
            if self._n_loops_running > 0:
                return
            self._n_loops_running += 1
            my_run_id = self._run_id
        try:
            while True:
                await asyncio.sleep(1 / TICK_HZ)
                caption = None
                reached_terminal = False
                async with self:
                    if my_run_id != self._run_id or not self.playing:
                        return
                    self.age_years += (
                        self.speed_multiplier * SIM_YEARS_PER_SECOND_AT_1X / TICK_HZ
                    )
                    prev_stage = self.stage
                    snap = evolve(self.mass_msun, self.age_years)
                    self._apply_snapshot(snap)
                    if snap.stage != prev_stage:
                        self.event_flag = f"entered_{snap.stage}"
                        caption = STAGE_CAPTIONS.get(snap.stage)
                    else:
                        self.event_flag = ""
                    if snap.stage in TERMINAL_STAGES:
                        self.playing = False
                        reached_terminal = True
                # Yield the toast (and return) outside `async with self` so the
                # state lock is released before handing control back to the
                # event loop/frontend.
                if caption:
                    yield rx.toast.info(caption, duration=6000, close_button=True)
                if reached_terminal:
                    return
        finally:
            async with self:
                self._n_loops_running -= 1

    @rx.var(cache=True)
    def age_display(self) -> str:
        years = self.age_years
        if years < 1e3:
            return f"{years:,.0f} yr"
        if years < 1e6:
            return f"{years / 1e3:,.1f} kyr"
        if years < 1e9:
            return f"{years / 1e6:,.2f} Myr"
        return f"{years / 1e9:,.2f} Gyr"

    @rx.var(cache=True)
    def is_terminal(self) -> bool:
        return self.stage in TERMINAL_STAGES

    @rx.var(cache=True)
    def mass_display(self) -> str:
        return f"{self.mass_msun:.1f}"

    @rx.var(cache=True)
    def temperature_display(self) -> str:
        return f"{self.temperature_k:,.0f}"

    @rx.var(cache=True)
    def luminosity_display(self) -> str:
        return f"{self.luminosity_lsun:.4g}"

    @rx.var(cache=True)
    def radius_display(self) -> str:
        return f"{self.radius_rsun:.4g}"

    @rx.var(cache=True)
    def speed_display(self) -> str:
        return f"{self.speed_multiplier:g}"

    @rx.var(cache=True)
    def stage_progress_pct(self) -> int:
        return round(self.stage_progress * 100)

    @rx.var(cache=True)
    def stage_track_list(self) -> list[str]:
        return list(stage_track(self.mass_msun))

    @rx.var(cache=True)
    def current_stage_index(self) -> int:
        track = stage_track(self.mass_msun)
        return track.index(self.stage) if self.stage in track else 0
