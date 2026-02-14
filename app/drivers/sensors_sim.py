from __future__ import annotations
import math
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal

from ..domain.models import Reading
from ..core.timeutil import now_utc


PatternType = Literal["manual", "sine", "step", "ramp", "random"]


@dataclass
class PatternConfig:
    type: PatternType = "manual"
    baseline: float = 3000.0
    amplitude: float = 1500.0
    period_s: float = 600.0
    noise: float = 50.0
    step_low: float = 2500.0
    step_high: float = 6500.0
    step_period_s: float = 120.0
    ramp_min: float = 2000.0
    ramp_max: float = 7000.0
    ramp_period_s: float = 600.0


class SimulatedLuxSensor:
    sensor_id = "lux_sim_01"
    unit = "lux"

    def __init__(self) -> None:
        self._enabled = True
        self._manual_value: Optional[float] = 3500.0
        self._pattern = PatternConfig()
        self._t0 = now_utc()

        # Optional: inject occasional failures for testing
        self._failure_rate = 0.0  # set to e.g. 0.02 to simulate 2% failures

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def set_manual(self, lux: float) -> None:
        self._pattern.type = "manual"
        self._manual_value = float(lux)

    def set_pattern(self, cfg: PatternConfig) -> None:
        self._pattern = cfg
        if cfg.type != "manual":
            self._manual_value = None

    def status(self) -> dict:
        return {
            "enabled": self._enabled,
            "manual_value": self._manual_value,
            "pattern": self._pattern.__dict__,
        }

    def _pattern_value(self, t: float) -> float:
        p = self._pattern
        if p.type == "manual":
            return float(self._manual_value if self._manual_value is not None else p.baseline)

        if p.type == "sine":
            val = p.baseline + p.amplitude * math.sin(2 * math.pi * t / max(p.period_s, 1.0))
            return val

        if p.type == "step":
            phase = (t % max(p.step_period_s, 1.0)) / max(p.step_period_s, 1.0)
            return p.step_high if phase >= 0.5 else p.step_low

        if p.type == "ramp":
            phase = (t % max(p.ramp_period_s, 1.0)) / max(p.ramp_period_s, 1.0)
            return p.ramp_min + (p.ramp_max - p.ramp_min) * phase

        if p.type == "random":
            return p.baseline + random.uniform(-p.amplitude, p.amplitude)

        return p.baseline

    async def read(self) -> Reading:
        ts = now_utc()
        if not self._enabled:
            return Reading(ts_utc=ts, sensor_id=self.sensor_id, value=0.0, unit=self.unit, ok=False, error="Sim sensor disabled")

        if self._failure_rate > 0.0 and random.random() < self._failure_rate:
            return Reading(ts_utc=ts, sensor_id=self.sensor_id, value=0.0, unit=self.unit, ok=False, error="Simulated read failure")

        t = (ts - self._t0).total_seconds()
        base = self._pattern_value(t)
        noisy = base + random.uniform(-self._pattern.noise, self._pattern.noise)
        val = max(0.0, noisy)
        return Reading(ts_utc=ts, sensor_id=self.sensor_id, value=val, unit=self.unit, ok=True, error=None)
