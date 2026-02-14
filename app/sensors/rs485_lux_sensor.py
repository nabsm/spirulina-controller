from __future__ import annotations

from dataclasses import dataclass
import logging

from .base import Sensor
from ..drivers.rs485_modbus import RS485ModbusRTU

logger = logging.getLogger(__name__)


@dataclass
class LuxRegisterSpec:
    functioncode: int = 3  # 3=holding, 4=input
    address: int = 0
    count: int = 1
    scale: float = 1.0     # e.g. 0.1 if sensor returns lux*10


class RS485LuxSensor(Sensor):
    def __init__(
        self,
        driver: RS485ModbusRTU,
        spec: LuxRegisterSpec = LuxRegisterSpec(),
        sensor_id: str = "lux_rs485",
    ):
        self._driver = driver
        self._spec = spec
        self._sensor_id = sensor_id

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    @property
    def unit(self) -> str:
        return "lux"

    def read(self) -> float:
        # Allow driver to connect lazily
        if self._spec.functioncode == 3:
            regs = self._driver.read_holding_registers(self._spec.address, self._spec.count)
        elif self._spec.functioncode == 4:
            regs = self._driver.read_input_registers(self._spec.address, self._spec.count)
        else:
            raise ValueError(f"Unsupported functioncode: {self._spec.functioncode}")

        if not regs:
            raise RuntimeError("No registers returned")

        raw = regs[0]
        lux = float(raw) * float(self._spec.scale)
        return lux
