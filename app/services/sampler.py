from __future__ import annotations
import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..core.timeutil import now_utc, now_local
from ..core.config import settings
from ..domain.interfaces import Sensor, Actuator, Repository
from ..domain.schedule import SchedulePolicy
from ..domain.controller import LuxController
from ..domain.models import ActionEvent, Reading

from app.sensors.base import SensorReading
from app.core.timeutil import now_utc


logger = logging.getLogger(__name__)


@dataclass
class LiveState:
    last_reading: Optional[Reading] = None
    avg_lux_30s: Optional[float] = None
    light_state: bool = False
    controller_enabled: bool = True
    override_active: bool = False
    mode: str = "sim"
    active_window_label: Optional[str] = None
    active_min_lux: Optional[float] = None
    active_max_lux: Optional[float] = None
    last_decision: Optional[str] = None
    last_reason: Optional[str] = None


class SamplerService:
    def __init__(
        self,
        sensor: Sensor,
        actuator: Actuator,
        repo: Repository,
        schedule: SchedulePolicy,
        controller: LuxController,
    ) -> None:
        self._sensor = sensor
        self._actuator = actuator
        self._repo = repo
        self._schedule = schedule
        self._controller = controller

        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

        self._buf = deque(maxlen=settings.avg_samples)
        self.live = LiveState(mode=settings.mode)

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="sampler_loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
            self._task = None

    async def _run(self) -> None:
        logger.info(
            "Sampler loop started (sample_seconds=%s avg_samples=%s)",
            settings.sample_seconds,
            settings.avg_samples,
        )

        while not self._stop.is_set():
            reading: Optional[SensorReading] = None
            thr = None
            avg_lux: Optional[float] = None

            try:
                # 1) Read sensor (sync call — run in thread to avoid blocking event loop)
                loop = asyncio.get_running_loop()
                sensor_type = type(self._sensor).__name__
                logger.debug("Reading sensor type=%s id=%s", sensor_type, getattr(self._sensor, "sensor_id", "?"))
                lux = await loop.run_in_executor(None, self._sensor.read)
                logger.info("Sensor read OK: lux=%.3f (sensor=%s)", lux, getattr(self._sensor, "sensor_id", "?"))

                # 2) Wrap into structured reading
                reading = SensorReading(
                    ts_utc=now_utc(),
                    value=float(lux),
                    ok=True,
                    error=None,
                    sensor_id=getattr(self._sensor, "sensor_id", "unknown"),
                    unit=getattr(self._sensor, "unit", "") or "",
                )

            except Exception as e:
                # Fail-safe: record a failed reading (do NOT append to avg buffer)
                reading = SensorReading(
                    ts_utc=now_utc(),
                    value=None,
                    ok=False,
                    error=str(e),
                    sensor_id=getattr(self._sensor, "sensor_id", "unknown"),
                    unit=getattr(self._sensor, "unit", "") or "",
                )
                logger.exception("Sensor read FAILED: %s", e)

            try:
                # 3) Persist reading (repo expects SensorReading, not float)
                self.live.last_reading = reading
                await self._repo.insert_reading(reading)

                # 4) Update rolling buffer & average only on ok readings
                if reading.ok and reading.value is not None:
                    self._buf.append(float(reading.value))

                if len(self._buf) == settings.avg_samples:
                    avg_lux = sum(self._buf) / float(len(self._buf))
                else:
                    avg_lux = None

                self.live.avg_lux_30s = avg_lux

                # 5) Update controller flags in live snapshot
                self.live.controller_enabled = self._controller.state.enabled
                self.live.override_active = self._controller.state.override_active

                # 6) Determine thresholds by schedule (local time)
                thr = self._schedule.active_thresholds(now_local())
                if thr:
                    self.live.active_window_label = thr.window_label
                    self.live.active_min_lux = thr.min_lux
                    self.live.active_max_lux = thr.max_lux
                else:
                    self.live.active_window_label = None
                    self.live.active_min_lux = None
                    self.live.active_max_lux = None

                # 7) Get current actuator state
                current_state = await self._actuator.get_state()
                self.live.light_state = current_state

                # 8) Decide
                decision = self._controller.decide(
                    now_utc=now_utc(),
                    avg_lux=avg_lux,
                    thresholds=thr,
                    current_light_state=current_state,
                    sensor_ok=reading.ok,
                )
                self.live.last_decision = decision.action
                self.live.last_reason = decision.reason

                # 9) Apply action (only when decision requires a change)
                if decision.action in ("ON", "OFF"):
                    desired = (decision.action == "ON")
                    if desired != current_state:
                        await self._actuator.set_state(desired, decision.reason)
                        self._controller.mark_switched(now_utc())

                        await self._repo.insert_action(
                            ActionEvent(
                                ts_utc=now_utc(),
                                actuator_id=self._actuator.actuator_id,
                                state=desired,
                                reason=decision.reason,
                                avg_lux=decision.avg_lux,
                                min_lux=decision.thresholds.min_lux if decision.thresholds else None,
                                max_lux=decision.thresholds.max_lux if decision.thresholds else None,
                                window_label=decision.thresholds.window_label if decision.thresholds else None,
                            )
                        )
                        self.live.light_state = desired

            except Exception as e:
                logger.exception("Sampler loop error: %s", e)

            # 10) sleep with cancellation awareness
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.sample_seconds)
            except asyncio.TimeoutError:
                pass

        logger.info("Sampler loop stopped")
    
