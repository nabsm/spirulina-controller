from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Reading:
    ts_utc: datetime
    sensor_id: str
    value: float
    unit: str = "lux"
    ok: bool = True
    error: Optional[str] = None


@dataclass(frozen=True)
class Thresholds:
    min_lux: float
    max_lux: float
    window_label: str


@dataclass(frozen=True)
class ControlDecision:
    action: str  # "ON" | "OFF" | "NOOP" | "BLOCKED" | "FAILSAFE"
    reason: str
    thresholds: Optional[Thresholds]
    avg_lux: Optional[float]


@dataclass(frozen=True)
class ActionEvent:
    ts_utc: datetime
    actuator_id: str
    state: bool
    reason: str
    avg_lux: Optional[float]
    min_lux: Optional[float]
    max_lux: Optional[float]
    window_label: Optional[str]
