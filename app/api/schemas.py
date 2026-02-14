from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal, List


class OverrideRequest(BaseModel):
    state: bool
    duration_s: int = Field(ge=1, le=24 * 3600)


class TimeWindowIn(BaseModel):
    id: str
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    min_lux: float
    max_lux: float
    enabled: bool = True
    priority: int = 0
    label: str = ""


class ScheduleReplaceRequest(BaseModel):
    windows: List[TimeWindowIn]


class SimManualRequest(BaseModel):
    lux: float = Field(ge=0)


class SimPatternRequest(BaseModel):
    type: Literal["manual", "sine", "step", "ramp", "random"]
    baseline: float = 3000
    amplitude: float = 1500
    period_s: float = 600
    noise: float = 50
    step_low: float = 2500
    step_high: float = 6500
    step_period_s: float = 120
    ramp_min: float = 2000
    ramp_max: float = 7000
    ramp_period_s: float = 600
