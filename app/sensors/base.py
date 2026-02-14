from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SensorReading:
    ts_utc: datetime
    value: float | None
    ok: bool
    error: str | None = None
    sensor_id: str = "unknown"
    unit: str = ""


class Sensor(ABC):
    """Domain-facing sensor abstraction."""

    @property
    @abstractmethod
    def sensor_id(self) -> str:
        ...

    @property
    def unit(self) -> str:
        return ""

    @abstractmethod
    def read(self) -> float:
        """Return a scalar reading (e.g., lux). Raise on failure."""
        ...
