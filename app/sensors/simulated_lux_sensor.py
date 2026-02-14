from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from threading import Lock

from .base import Sensor


@dataclass
class PatternConfig:
    type: str = "sine"     # sine|step|ramp|random
    baseline: float = 4000
    amplitude: float = 2000
    period_s: float = 600
    noise: float = 50

    step_low: float = 2500
    step_high: float = 6500
    step_period_s: float = 120

    ramp_min: float = 2000
    ramp_max: float = 7000
    ramp_period_s: float = 600


class SimulatedLuxSensor(Sensor):
    def __init__(self, sensor_id: str = "lux_sim"):
        self._sensor_id = sensor_id
        self._lock = Lock()
        self._enabled = True
        self._mode = "manual"   # manual|pattern
        self._manual_lux = 3500.0
        self._pattern = PatternConfig()

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    @property
    def unit(self) -> str:
        return "lux"

    def enable(self) -> None:
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        with self._lock:
            self._enabled = False

    def set_manual(self, lux: float) -> None:
        with self._lock:
            self._mode = "manual"
            self._manual_lux = float(lux)

    def set_pattern(self, cfg: PatternConfig) -> None:
        with self._lock:
            self._mode = "pattern"
            self._pattern = cfg

    def status(self) -> dict:
        with self._lock:
            return {
                "enabled": self._enabled,
                "mode": self._mode,
                "manual_lux": self._manual_lux,
                "pattern": self._pattern.__dict__,
            }

    def read(self) -> float:
        with self._lock:
            if not self._enabled:
                raise RuntimeError("Simulated sensor disabled")

            if self._mode == "manual":
                return float(self._manual_lux)

            cfg = self._pattern

        t = time.time()

        if cfg.type == "sine":
            phase = (t % cfg.period_s) / cfg.period_s * 2.0 * math.pi
            v = cfg.baseline + cfg.amplitude * math.sin(phase)

        elif cfg.type == "step":
            half = cfg.step_period_s / 2.0
            v = cfg.step_high if (t % cfg.step_period_s) < half else cfg.step_low

        elif cfg.type == "ramp":
            frac = (t % cfg.ramp_period_s) / cfg.ramp_period_s
            v = cfg.ramp_min + (cfg.ramp_max - cfg.ramp_min) * frac

        elif cfg.type == "random":
            v = cfg.baseline + random.uniform(-cfg.amplitude, cfg.amplitude)

        else:
            v = cfg.baseline

        if cfg.noise > 0:
            v += random.uniform(-cfg.noise, cfg.noise)

        return float(max(0.0, v))
