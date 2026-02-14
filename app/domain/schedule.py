from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional
from .models import Thresholds


@dataclass(frozen=True)
class TimeWindow:
    id: str
    start: time
    end: time
    min_lux: float
    max_lux: float
    enabled: bool = True
    priority: int = 0  # higher wins
    label: str = ""

    def matches(self, t: time) -> bool:
        # Handle overnight windows (e.g., 22:00 -> 02:00)
        if self.start <= self.end:
            return self.start <= t < self.end
        return t >= self.start or t < self.end


class SchedulePolicy:
    def __init__(self, windows: list[TimeWindow]) -> None:
        self._windows = windows

    def windows(self) -> list[TimeWindow]:
        return list(self._windows)

    def replace(self, windows: list[TimeWindow]) -> None:
        self._windows = windows

    def active_thresholds(self, local_dt: datetime) -> Optional[Thresholds]:
        t = local_dt.timetz().replace(tzinfo=None)
        candidates = [w for w in self._windows if w.enabled and w.matches(t)]
        if not candidates:
            return None
        candidates.sort(key=lambda w: w.priority, reverse=True)
        w = candidates[0]
        label = w.label or f"{w.start.strftime('%H:%M')}-{w.end.strftime('%H:%M')}"
        return Thresholds(min_lux=w.min_lux, max_lux=w.max_lux, window_label=label)
