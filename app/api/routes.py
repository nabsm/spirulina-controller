from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..core.config import Settings, settings
from ..core.timeutil import now_utc, now_local
from ..domain.controller import LuxController
from ..domain.schedule import TimeWindow, SchedulePolicy
from ..drivers.sensors_sim import PatternConfig, SimulatedLuxSensor
from ..services.sampler import SamplerService
from ..storage.sqlite_repo import SQLiteRepository
from .schemas import (
    OverrideRequest,
    ScheduleReplaceRequest,
    SimManualRequest,
    SimPatternRequest,
    SettingsUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Dependency getters (imported from main via circular-safe approach) ---
# We define them here as callables that main.py will set via app.dependency_overrides.
def get_sampler() -> SamplerService:  # overridden in main
    raise RuntimeError("Sampler dependency not configured")

def get_controller() -> LuxController:  # overridden in main
    raise RuntimeError("Controller dependency not configured")

def get_schedule() -> SchedulePolicy:  # overridden in main
    raise RuntimeError("Schedule dependency not configured")

def get_repo() -> SQLiteRepository:  # overridden in main
    raise RuntimeError("Repo dependency not configured")

def get_sim_sensor() -> SimulatedLuxSensor:  # overridden in main
    raise RuntimeError("Simulated sensor dependency not configured")


def _parse_hhmm(s: str):
    try:
        h, m = s.split(":")
        return int(h), int(m)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {s}, expected HH:MM")


def _to_time(s: str):
    from datetime import time
    h, m = _parse_hhmm(s)
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise HTTPException(status_code=400, detail=f"Invalid time: {s}")
    return time(hour=h, minute=m)


@router.get("/live")
async def get_live(svc: SamplerService = Depends(get_sampler)):
    r = svc.live.last_reading
    return {
        "app": settings.app_name,
        "mode": svc.live.mode,
        "now_local": now_local().isoformat(),
        "last_reading": {
            "ts_utc": r.ts_utc.isoformat() if r else None,
            "value": r.value if r else None,
            "ok": r.ok if r else None,
            "error": r.error if r else None,
            "sensor_id": r.sensor_id if r else None,
            "unit": r.unit if r else None,
        },
        "avg_lux_30s": svc.live.avg_lux_30s,
        "thresholds": {
            "window_label": svc.live.active_window_label,
            "min_lux": svc.live.active_min_lux,
            "max_lux": svc.live.active_max_lux,
        },
        "light_state": svc.live.light_state,
        "controller": {
            "enabled": svc.live.controller_enabled,
            "override_active": svc.live.override_active,
            "last_decision": svc.live.last_decision,
            "last_reason": svc.live.last_reason,
        },
    }


@router.post("/controller/enable")
async def controller_enable(ctrl: LuxController = Depends(get_controller)):
    ctrl.enable()
    return {"ok": True, "enabled": ctrl.state.enabled}


@router.post("/controller/disable")
async def controller_disable(ctrl: LuxController = Depends(get_controller)):
    ctrl.disable()
    return {"ok": True, "enabled": ctrl.state.enabled}


@router.post("/controller/override")
async def controller_override(req: OverrideRequest, ctrl: LuxController = Depends(get_controller)):
    until = now_utc() + timedelta(seconds=req.duration_s)
    ctrl.set_override(req.state, until)
    return {"ok": True, "override_active": True, "until_utc": until.isoformat()}


@router.post("/controller/override/cancel")
async def controller_override_cancel(ctrl: LuxController = Depends(get_controller)):
    ctrl.cancel_override()
    return {"ok": True, "override_active": False}


@router.get("/schedule")
async def get_schedule_api(schedule: SchedulePolicy = Depends(get_schedule)):
    out = []
    for w in schedule.windows():
        out.append({
            "id": w.id,
            "start_time": w.start.strftime("%H:%M"),
            "end_time": w.end.strftime("%H:%M"),
            "min_lux": w.min_lux,
            "max_lux": w.max_lux,
            "enabled": w.enabled,
            "priority": w.priority,
            "label": w.label,
        })
    return {"windows": out}


@router.get("/schedule/defaults")
async def get_schedule_defaults():
    defaults_path = Path(__file__).resolve().parent.parent / "config" / "default_schedule.json"
    if not defaults_path.exists():
        raise HTTPException(status_code=404, detail="Default schedule file not found")
    data = json.loads(defaults_path.read_text())
    return data


@router.put("/schedule")
async def replace_schedule(
    req: ScheduleReplaceRequest,
    schedule: SchedulePolicy = Depends(get_schedule)
):
    windows: list[TimeWindow] = []
    for win in req.windows:
        windows.append(
            TimeWindow(
                id=win.id,
                start=_to_time(win.start_time),
                end=_to_time(win.end_time),
                min_lux=float(win.min_lux),
                max_lux=float(win.max_lux),
                enabled=bool(win.enabled),
                priority=int(win.priority),
                label=win.label or "",
            )
        )
    schedule.replace(windows)
    return {"ok": True, "count": len(windows)}


@router.get("/readings")
async def readings(
    minutes: int = 60,
    limit: int = 5000,
    repo: SQLiteRepository = Depends(get_repo),
):
    end = now_utc()
    start = end - timedelta(minutes=max(1, minutes))
    rows = await repo.query_readings(start.isoformat(), end.isoformat(), limit=min(limit, 20000))
    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "rows": [
            {"ts_utc": r.ts_utc.isoformat(), "value": r.value, "ok": r.ok, "error": r.error}
            for r in rows
        ],
    }


@router.get("/actions")
async def actions(
    minutes: int = 240,
    limit: int = 2000,
    repo: SQLiteRepository = Depends(get_repo),
):
    end = now_utc()
    start = end - timedelta(minutes=max(1, minutes))
    rows = await repo.query_actions(start.isoformat(), end.isoformat(), limit=min(limit, 20000))
    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "rows": [
            {
                "ts_utc": a.ts_utc.isoformat(),
                "state": a.state,
                "reason": a.reason,
                "avg_lux": a.avg_lux,
                "min_lux": a.min_lux,
                "max_lux": a.max_lux,
                "window_label": a.window_label,
            }
            for a in rows
        ],
    }


# --- Simulation endpoints ---
@router.get("/sim/status")
async def sim_status(sensor: SimulatedLuxSensor = Depends(get_sim_sensor)):
    return sensor.status()


@router.post("/sim/enable")
async def sim_enable(sensor: SimulatedLuxSensor = Depends(get_sim_sensor)):
    sensor.enable()
    return {"ok": True, "enabled": True}


@router.post("/sim/disable")
async def sim_disable(sensor: SimulatedLuxSensor = Depends(get_sim_sensor)):
    sensor.disable()
    return {"ok": True, "enabled": False}


@router.post("/sim/lux/manual")
async def sim_set_manual(req: SimManualRequest, sensor: SimulatedLuxSensor = Depends(get_sim_sensor)):
    sensor.set_manual(req.lux)
    return {"ok": True, "mode": "manual", "lux": req.lux}


@router.post("/sim/lux/pattern")
async def sim_set_pattern(req: SimPatternRequest, sensor: SimulatedLuxSensor = Depends(get_sim_sensor)):
    cfg = PatternConfig(**req.model_dump())
    sensor.set_pattern(cfg)
    return {"ok": True, "pattern": cfg.__dict__}


# --- Settings endpoints ---

RESTART_REQUIRED_KEYS = frozenset({
    "sensor_mode", "actuator_mode", "rs485_port", "rs485_baudrate",
    "rs485_slave_id", "lux_functioncode", "lux_register_address",
    "lux_register_count", "lux_scale", "sqlite_path",
})

# All Settings field names (for validation)
_SETTINGS_FIELDS = {name: field for name, field in Settings.model_fields.items()}


def _cast_setting_value(key: str, raw: object) -> object:
    """Cast a raw value to the type expected by the Settings field."""
    field = _SETTINGS_FIELDS.get(key)
    if field is None:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")
    annotation = field.annotation
    if annotation is bool or (hasattr(annotation, '__origin__') and annotation is bool):
        if isinstance(raw, str):
            return raw.lower() in ("true", "1", "yes")
        return bool(raw)
    if annotation is int:
        return int(raw)
    if annotation is float:
        return float(raw)
    if annotation is str:
        return str(raw)
    return raw


def get_actuator():  # overridden in main
    raise RuntimeError("Actuator dependency not configured")


@router.get("/settings")
async def get_settings():
    current = {}
    for key in _SETTINGS_FIELDS:
        current[key] = getattr(settings, key)
    return {
        "settings": current,
        "restart_required_keys": list(RESTART_REQUIRED_KEYS),
    }


@router.put("/settings")
async def update_settings(
    req: SettingsUpdateRequest,
    repo: SQLiteRepository = Depends(get_repo),
):
    updated_keys = []
    db_updates: dict[str, str] = {}
    runtime_applied: list[str] = []

    for key, raw_value in req.updates.items():
        if key not in _SETTINGS_FIELDS:
            raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")

        typed_value = _cast_setting_value(key, raw_value)
        setattr(settings, key, typed_value)
        db_updates[key] = json.dumps(typed_value)
        updated_keys.append(key)

        if key not in RESTART_REQUIRED_KEYS:
            runtime_applied.append(key)

    # Hot-update Sonoff actuator connection params if changed
    sonoff_keys = {"sonoff_ip", "sonoff_port", "sonoff_device_id", "sonoff_timeout_seconds"}
    if sonoff_keys & set(updated_keys):
        try:
            act = get_actuator()
            from ..drivers.actuator_sonoff import SonoffBasicR3Actuator
            if isinstance(act, SonoffBasicR3Actuator):
                act._base_url = f"http://{settings.sonoff_ip}:{settings.sonoff_port}"
                act._device_id = settings.sonoff_device_id
                act._timeout = settings.sonoff_timeout_seconds
                logger.info("Hot-updated Sonoff actuator connection params")
        except Exception:
            pass  # actuator not available or not sonoff

    await repo.set_settings_batch(db_updates)

    return {"ok": True, "updated_keys": updated_keys, "runtime_applied": runtime_applied}


@router.post("/settings/discover-sonoff")
async def discover_sonoff():
    from ..services.mdns_discovery import discover_sonoff_devices
    devices = await discover_sonoff_devices(timeout=3.0)
    return {"devices": devices}
