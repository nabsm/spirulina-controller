# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack IoT lighting controller for spirulina cultivation. Monitors ambient lux via sensors (RS485 Modbus RTU or simulated) and automatically toggles LED grow lights based on configurable time-windowed schedules with hysteresis.

## Development Commands

### Backend
```bash
# Activate venv
source venv/bin/activate

# Run backend in simulation mode (default)
SENSOR_MODE=sim uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend with RS485 hardware
SENSOR_MODE=rs485 RS485_PORT=/dev/ttyUSB0 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd dashboard
npm install    # first time only
npm run dev    # dev server at :5173, proxies /api to :8000
npm run build  # production build
npm run lint   # ESLint
```

### No test suite exists yet.

## Architecture

**Backend** (Python 3.11, FastAPI, async): Layered architecture with protocol-based dependency injection.

```
app/
├── main.py              # App init, lifespan, DI wiring of singletons
├── core/config.py       # Pydantic Settings (all env vars with defaults)
├── domain/
│   ├── interfaces.py    # Protocol definitions: Sensor, Actuator, Repository
│   ├── controller.py    # LuxController – core decision logic (hysteresis, anti-chatter, fail-safe)
│   ├── schedule.py      # TimeWindow + SchedulePolicy (time-windowed thresholds, overnight spans)
│   └── models.py        # Reading, ControlDecision, ActionEvent dataclasses
├── drivers/             # Hardware abstractions (rs485_modbus.py, sensors_sim.py, actuators_sim.py)
├── sensors/             # Sensor implementations (simulated + RS485 lux)
├── storage/sqlite_repo.py  # Async aiosqlite repository
├── services/sampler.py  # Main async control loop (read→average→decide→act→persist)
└── api/
    ├── routes.py        # All REST endpoints under /api
    └── schemas.py       # Pydantic request/response models
```

**Frontend** (React 19, Vite, Tailwind CSS, Recharts):
- `dashboard/src/components/Dashboard.jsx` – main UI, polls `/api/live` every 2.5s, readings/actions every 20s
- `dashboard/src/lib/api.js` – fetch wrapper for all endpoints
- `dashboard/src/components/ui.jsx` – reusable UI primitives

## Control Loop (sampler.py)

Every 5s: read sensor → update rolling average (6 samples / 30s) → match active schedule window → `LuxController.decide()` → toggle actuator if state changed → persist reading + action to SQLite.

Decision logic: hysteresis band around min/max lux thresholds, minimum switch interval (60s default), fail-safe on sensor fault, override support with duration.

## Key Configuration (env vars, defaults in core/config.py)

| Variable | Default | Purpose |
|---|---|---|
| `SENSOR_MODE` | `sim` | `sim` or `rs485` |
| `SAMPLE_SECONDS` | `5` | Sampling interval |
| `AVG_SAMPLES` | `6` | Rolling average window |
| `HYSTERESIS_LUX` | `50.0` | Lux band to prevent flapping |
| `MIN_SWITCH_INTERVAL_SECONDS` | `60` | Anti-chatter guard |
| `DEFAULT_MIN_LUX` / `DEFAULT_MAX_LUX` | `3000` / `6000` | Default thresholds |
| `SQLITE_PATH` | `spirulina.db` | Database file |
| `FAIL_SAFE_LIGHT_STATE` | `false` | Light state on sensor failure |
| `TZ` | `Asia/Kuala_Lumpur` | Local timezone for schedule matching |

## Conventions

- Python: type hints throughout, `from __future__ import annotations`, snake_case
- Frontend: functional components with hooks, camelCase
- All times stored as UTC internally, converted to local for display/schedule matching
- Database auto-initializes on startup (no migrations)
- Logging: rotating file (`spirulina.log`, 2MB max, 5 backups) + console, INFO level
