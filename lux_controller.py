#!/usr/bin/env python3
"""
Standalone lux controller.

Reads an RS485 Modbus RTU lux sensor over USB, maintains a rolling average,
and toggles a light relay based on min/max lux thresholds with hysteresis.

Usage:
    python lux_controller.py                        # defaults
    python lux_controller.py --port /dev/ttyUSB0    # specify port
    python lux_controller.py --min-lux 2000 --max-lux 5000

Dependencies:
    pip install pymodbus pyserial
"""

from __future__ import annotations

import argparse
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pymodbus.client import ModbusSerialClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Config:
    # RS485 / Modbus
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    slave_id: int = 1
    function_code: int = 3        # 3=holding, 4=input registers
    register_address: int = 2
    register_count: int = 2
    lux_scale: float = 0.001      # raw = (hi<<16)|lo, lux = raw/1000

    # Sampling
    sample_interval_s: float = 6.0
    avg_window_s: float = 30.0    # average over this many seconds

    # Thresholds
    min_lux: float = 3000.0       # below this avg → light ON
    max_lux: float = 6000.0       # above this avg → light OFF
    hysteresis: float = 50.0      # dead band around thresholds

    # Anti-chatter
    min_switch_interval_s: float = 60.0

    @property
    def avg_samples(self) -> int:
        return max(1, int(self.avg_window_s / self.sample_interval_s))


# ---------------------------------------------------------------------------
# Relay stub — replace with your real USB relay implementation
# ---------------------------------------------------------------------------

class RelayStub:
    """
    Stub relay that logs ON/OFF.

    To implement a real relay, subclass or replace this with one of:
      - HID USB relay: use `usb.core` or `hidapi` to send feature reports
      - Serial USB relay: open the relay's serial port and send command bytes
      - GPIO relay: use RPi.GPIO or gpiozero to toggle a pin

    The interface is just two methods: turn_on() and turn_off().
    """

    def __init__(self) -> None:
        self._state = False

    @property
    def state(self) -> bool:
        return self._state

    def turn_on(self) -> None:
        if not self._state:
            self._state = True
            logging.info("RELAY → ON")

    def turn_off(self) -> None:
        if self._state:
            self._state = False
            logging.info("RELAY → OFF")


# ---------------------------------------------------------------------------
# Sensor reader
# ---------------------------------------------------------------------------

class LuxSensor:
    """Read lux from an RS485 Modbus RTU sensor."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._client = ModbusSerialClient(
            port=cfg.port,
            baudrate=cfg.baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1.0,
        )
        self._connected = False

    def _ensure_connected(self) -> None:
        if not self._connected:
            ok = self._client.connect()
            if not ok:
                raise ConnectionError(f"Cannot connect to {self._cfg.port}")
            self._connected = True
            logging.info("Connected to %s @ %d baud", self._cfg.port, self._cfg.baudrate)

    def read(self) -> float:
        """Return a single lux reading. Raises on failure."""
        self._ensure_connected()

        cfg = self._cfg
        if cfg.function_code == 4:
            resp = self._client.read_input_registers(
                address=cfg.register_address,
                count=cfg.register_count,
                device_id=cfg.slave_id,
            )
        else:
            resp = self._client.read_holding_registers(
                address=cfg.register_address,
                count=cfg.register_count,
                device_id=cfg.slave_id,
            )

        if resp.isError():
            self._connected = False
            raise RuntimeError(f"Modbus error: {resp}")

        raw = 0
        for r in resp.registers:
            raw = (raw << 16) | r
        return raw * cfg.lux_scale

    def close(self) -> None:
        if self._connected:
            self._client.close()
            self._connected = False


# ---------------------------------------------------------------------------
# Controller logic
# ---------------------------------------------------------------------------

@dataclass
class ControllerState:
    light_on: bool = False
    last_switch_time: float = 0.0
    samples: deque = field(default_factory=deque)

    def add_sample(self, value: float, max_samples: int) -> None:
        self.samples.append(value)
        while len(self.samples) > max_samples:
            self.samples.popleft()

    @property
    def avg(self) -> float | None:
        if not self.samples:
            return None
        return sum(self.samples) / len(self.samples)


def decide(avg_lux: float, cfg: Config, state: ControllerState, now: float) -> bool | None:
    """
    Decide whether to switch. Returns True (turn on), False (turn off),
    or None (no change).

    Logic:
      - If avg < min_lux - hysteresis  → light ON  (not enough ambient light)
      - If avg > max_lux + hysteresis  → light OFF (plenty of ambient light)
      - Otherwise                      → hold current state (inside dead band)
    """
    if now - state.last_switch_time < cfg.min_switch_interval_s:
        return None  # anti-chatter guard

    turn_on_threshold = cfg.min_lux - cfg.hysteresis
    turn_off_threshold = cfg.max_lux + cfg.hysteresis

    if avg_lux < turn_on_threshold and not state.light_on:
        return True
    if avg_lux > turn_off_threshold and state.light_on:
        return False

    return None


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(cfg: Config) -> None:
    log = logging.getLogger("controller")
    sensor = LuxSensor(cfg)
    relay = RelayStub()
    state = ControllerState()

    log.info("Starting lux controller")
    log.info("  Port:       %s @ %d baud (slave %d)", cfg.port, cfg.baudrate, cfg.slave_id)
    log.info("  Sampling:   every %.1fs, avg over %d samples (%.0fs window)",
             cfg.sample_interval_s, cfg.avg_samples, cfg.avg_window_s)
    log.info("  Thresholds: min=%g  max=%g  hysteresis=%g", cfg.min_lux, cfg.max_lux, cfg.hysteresis)
    log.info("  Anti-chatter: %.0fs minimum switch interval", cfg.min_switch_interval_s)

    try:
        while True:
            # --- Read sensor ---
            try:
                lux = sensor.read()
                state.add_sample(lux, cfg.avg_samples)
            except Exception as e:
                log.warning("Sensor read failed: %s", e)
                time.sleep(cfg.sample_interval_s)
                continue

            avg = state.avg
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

            log.info(
                "[%s] lux=%.0f  avg=%.0f (%d/%d samples)  light=%s",
                ts, lux, avg, len(state.samples), cfg.avg_samples,
                "ON" if state.light_on else "OFF",
            )

            # --- Decide ---
            if avg is not None and len(state.samples) >= cfg.avg_samples:
                action = decide(avg, cfg, state, time.monotonic())

                if action is True:
                    relay.turn_on()
                    state.light_on = True
                    state.last_switch_time = time.monotonic()
                    log.info("→ LIGHT ON  (avg %.0f < %.0f)", avg, cfg.min_lux - cfg.hysteresis)

                elif action is False:
                    relay.turn_off()
                    state.light_on = False
                    state.last_switch_time = time.monotonic()
                    log.info("→ LIGHT OFF (avg %.0f > %.0f)", avg, cfg.max_lux + cfg.hysteresis)

            time.sleep(cfg.sample_interval_s)

    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        sensor.close()
        relay.turn_off()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Standalone RS485 lux controller")

    p.add_argument("--port", default="/dev/ttyUSB0", help="Serial port (default: /dev/ttyUSB0)")
    p.add_argument("--baudrate", type=int, default=9600)
    p.add_argument("--slave-id", type=int, default=1)
    p.add_argument("--function-code", type=int, default=3, choices=[3, 4],
                   help="Modbus function code: 3=holding, 4=input registers")
    p.add_argument("--register", type=int, default=2, help="Register address")
    p.add_argument("--count", type=int, default=2, help="Number of registers to read")
    p.add_argument("--scale", type=float, default=0.001, help="Raw register → lux multiplier")

    p.add_argument("--sample-interval", type=float, default=6.0, help="Seconds between reads")
    p.add_argument("--avg-window", type=float, default=30.0, help="Averaging window in seconds")

    p.add_argument("--min-lux", type=float, default=3000.0, help="Below this avg → light ON")
    p.add_argument("--max-lux", type=float, default=6000.0, help="Above this avg → light OFF")
    p.add_argument("--hysteresis", type=float, default=50.0, help="Dead band around thresholds")
    p.add_argument("--min-switch-interval", type=float, default=60.0,
                   help="Minimum seconds between state changes")

    p.add_argument("--verbose", "-v", action="store_true", help="Debug logging")

    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    cfg = Config(
        port=args.port,
        baudrate=args.baudrate,
        slave_id=args.slave_id,
        function_code=args.function_code,
        register_address=args.register,
        register_count=args.count,
        lux_scale=args.scale,
        sample_interval_s=args.sample_interval,
        avg_window_s=args.avg_window,
        min_lux=args.min_lux,
        max_lux=args.max_lux,
        hysteresis=args.hysteresis,
        min_switch_interval_s=args.min_switch_interval,
    )

    run(cfg)


if __name__ == "__main__":
    main()
