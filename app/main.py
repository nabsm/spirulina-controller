from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import time
from pathlib import Path

from fastapi import FastAPI

from .core.config import settings
from .core.log import configure_logging

from .api.routes import router as api_router
import app.api.routes as routes_module

from .drivers.sensors_sim import SimulatedLuxSensor
from .drivers.actuators_sim import SimulatedLightActuator
from .domain.controller import LuxController
from .domain.schedule import SchedulePolicy, TimeWindow
from .services.sampler import SamplerService
from .storage.sqlite_repo import SQLiteRepository

from .sensors.base import Sensor
from .sensors.simulated_lux_sensor import SimulatedLuxSensor
from .drivers.rs485_modbus import RS485ModbusRTU, ModbusRtuConfig
from .sensors.rs485_lux_sensor import RS485LuxSensor, LuxRegisterSpec


logger = logging.getLogger(__name__)


sensor: Sensor
sim_sensor: SimulatedLuxSensor | None = None
rs485_driver: RS485ModbusRTU | None = None

def build_sensor() -> Sensor:
    global sim_sensor, rs485_driver

    if settings.sensor_mode.lower() == "rs485":
        rs485_driver = RS485ModbusRTU(
            ModbusRtuConfig(
                port=settings.rs485_port,
                baudrate=settings.rs485_baudrate,
                slave_id=settings.rs485_slave_id,
            )
        )
        # lazy connect inside driver; or connect explicitly here:
        # rs485_driver.connect()

        spec = LuxRegisterSpec(
            functioncode=settings.lux_functioncode,
            address=settings.lux_register_address,
            count=settings.lux_register_count,
            scale=settings.lux_scale,
        )
        return RS485LuxSensor(driver=rs485_driver, spec=spec, sensor_id="lux_rs485")

    # default to sim
    sim_sensor = SimulatedLuxSensor()
    return sim_sensor

sensor = build_sensor()




# --- Singletons ---
actuator_sim = SimulatedLightActuator()
controller = LuxController()

def _load_default_windows() -> list[TimeWindow]:
    defaults_path = Path(__file__).resolve().parent / "config" / "default_schedule.json"
    try:
        data = json.loads(defaults_path.read_text())
        windows = []
        for w in data["windows"]:
            h1, m1 = w["start_time"].split(":")
            h2, m2 = w["end_time"].split(":")
            windows.append(TimeWindow(
                id=w["id"],
                start=time(int(h1), int(m1)),
                end=time(int(h2), int(m2)),
                min_lux=float(w["min_lux"]),
                max_lux=float(w["max_lux"]),
                enabled=bool(w.get("enabled", True)),
                priority=int(w.get("priority", 0)),
                label=w.get("label", ""),
            ))
        return windows
    except Exception as e:
        logger.warning("Failed to load default_schedule.json, using hardcoded defaults: %s", e)
        return [
            TimeWindow(id="morning", start=time(7, 0), end=time(11, 0), min_lux=3000, max_lux=6000, priority=10, label="Morning"),
            TimeWindow(id="midday", start=time(11, 0), end=time(15, 0), min_lux=3500, max_lux=6500, priority=10, label="Midday"),
            TimeWindow(id="afternoon", start=time(15, 0), end=time(19, 0), min_lux=3200, max_lux=6200, priority=10, label="Afternoon"),
        ]

schedule = SchedulePolicy(windows=_load_default_windows())

repo = SQLiteRepository(settings.sqlite_path)
sampler: SamplerService | None = None


def get_sampler() -> SamplerService:
    assert sampler is not None
    return sampler


def get_controller() -> LuxController:
    return controller


def get_schedule() -> SchedulePolicy:
    return schedule


def get_repo() -> SQLiteRepository:
    return repo


def get_sim_sensor() -> SimulatedLuxSensor:
    if sim_sensor is None:
        raise RuntimeError("Sim sensor not available (sensor_mode is not 'sim').")
    return sim_sensor


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting %s (mode=%s)", settings.app_name, settings.mode)

    await repo.init()

    global sampler
    sampler = SamplerService(
        sensor=sensor,
        actuator=actuator_sim,
        repo=repo,
        schedule=schedule,
        controller=controller,
    )
    await sampler.start()

    try:
        yield
    finally:
        if sampler:
            await sampler.stop()

        if rs485_driver is not None:
            rs485_driver.close()

        logger.info("Shutdown complete")





app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Make the dependency functions in routes resolve to the real ones
app.dependency_overrides[routes_module.get_sampler] = get_sampler
app.dependency_overrides[routes_module.get_controller] = get_controller
app.dependency_overrides[routes_module.get_schedule] = get_schedule
app.dependency_overrides[routes_module.get_repo] = get_repo
app.dependency_overrides[routes_module.get_sim_sensor] = get_sim_sensor

app.include_router(api_router, prefix="/api")
