from __future__ import annotations
from typing import Protocol, Optional, runtime_checkable
from .models import Reading, ActionEvent


@runtime_checkable
class Sensor(Protocol):
    sensor_id: str
    unit: str

    async def read(self) -> Reading:
        ...


@runtime_checkable
class Actuator(Protocol):
    actuator_id: str

    async def get_state(self) -> bool:
        ...

    async def set_state(self, on: bool, reason: str) -> None:
        ...


@runtime_checkable
class Repository(Protocol):
    async def init(self) -> None:
        ...

    async def insert_reading(self, reading: Reading) -> None:
        ...

    async def insert_action(self, action: ActionEvent) -> None:
        ...

    async def query_readings(self, start_ts: str, end_ts: str, limit: int) -> list[Reading]:
        ...

    async def query_actions(self, start_ts: str, end_ts: str, limit: int) -> list[ActionEvent]:
        ...
