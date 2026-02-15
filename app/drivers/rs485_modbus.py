from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from pymodbus.client import ModbusSerialClient

logger = logging.getLogger(__name__)


@dataclass
class ModbusRtuConfig:
    port: str = "/dev/ttyUSB0"      # Windows example: "COM3"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"               # "N", "E", "O"
    stopbits: int = 1
    timeout_s: float = 1.0
    slave_id: int = 1
    reconnect_backoff_s: float = 1.0
    max_reconnect_backoff_s: float = 10.0


class RS485ModbusRTU:
    """
    Modbus RTU over serial/USB driver.
    Responsible for: connect/reconnect, raw register reads.
    """

    def __init__(self, cfg: ModbusRtuConfig):
        self.cfg = cfg
        self._client = ModbusSerialClient(
            port=cfg.port,
            baudrate=cfg.baudrate,
            bytesize=cfg.bytesize,
            parity=cfg.parity,
            stopbits=cfg.stopbits,
            timeout=cfg.timeout_s,
            method="rtu",
        )
        self._connected = False
        self._backoff = cfg.reconnect_backoff_s

    def connect(self) -> None:
        if self._connected:
            return
        ok = self._client.connect()
        if not ok:
            raise RuntimeError(f"Unable to connect Modbus RTU on {self.cfg.port}")
        self._connected = True
        self._backoff = self.cfg.reconnect_backoff_s
        logger.info("Modbus RTU connected on %s (baud=%s)", self.cfg.port, self.cfg.baudrate)

    def close(self) -> None:
        try:
            self._client.close()
        finally:
            self._connected = False

    def _ensure_connected(self) -> None:
        if self._connected:
            return
        # reconnect loop with bounded backoff (non-blocking-ish; one attempt per call)
        try:
            self.connect()
        except Exception as e:
            logger.warning("Modbus reconnect failed: %s", e)
            time.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, self.cfg.max_reconnect_backoff_s)
            raise

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        """
        Function code 3. Returns list of 16-bit register values.
        """
        self._ensure_connected()
        rr = self._client.read_holding_registers(address=address, count=count, device_id=self.cfg.slave_id)
        if rr.isError():
            # Mark disconnected so next call attempts reconnect
            self._connected = False
            raise RuntimeError(f"Modbus read_holding_registers error: {rr}")
        return list(rr.registers)

    def read_input_registers(self, address: int, count: int) -> list[int]:
        """
        Function code 4. Returns list of 16-bit register values.
        """
        self._ensure_connected()
        rr = self._client.read_input_registers(address=address, count=count, device_id=self.cfg.slave_id)
        if rr.isError():
            self._connected = False
            raise RuntimeError(f"Modbus read_input_registers error: {rr}")
        return list(rr.registers)
