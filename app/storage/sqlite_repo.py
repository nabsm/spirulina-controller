from __future__ import annotations
import aiosqlite
from datetime import datetime, timezone
from typing import Dict, List
from ..domain.models import Reading, ActionEvent


class SQLiteRepository:
    def __init__(self, path: str) -> None:
        self._path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    ts_utc TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    error TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    ts_utc TEXT NOT NULL,
                    actuator_id TEXT NOT NULL,
                    state INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    avg_lux REAL,
                    min_lux REAL,
                    max_lux REAL,
                    window_label TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings(ts_utc)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(ts_utc)")
            await db.commit()

    async def insert_reading(self, r: Reading) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO readings(ts_utc,sensor_id,value,unit,ok,error) VALUES (?,?,?,?,?,?)",
                (r.ts_utc.isoformat(), r.sensor_id, float(r.value), r.unit, 1 if r.ok else 0, r.error),
            )
            await db.commit()

    async def insert_action(self, a: ActionEvent) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO actions(ts_utc,actuator_id,state,reason,avg_lux,min_lux,max_lux,window_label) VALUES (?,?,?,?,?,?,?,?)",
                (
                    a.ts_utc.isoformat(),
                    a.actuator_id,
                    1 if a.state else 0,
                    a.reason,
                    a.avg_lux,
                    a.min_lux,
                    a.max_lux,
                    a.window_label,
                ),
            )
            await db.commit()

    async def query_readings(self, start_ts: str, end_ts: str, limit: int) -> List[Reading]:
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                SELECT ts_utc,sensor_id,value,unit,ok,error
                FROM readings
                WHERE ts_utc >= ? AND ts_utc <= ?
                ORDER BY ts_utc DESC
                LIMIT ?
                """,
                (start_ts, end_ts, limit),
            )
            rows = await cur.fetchall()
        out: list[Reading] = []
        for ts, sid, val, unit, ok, err in rows:
            out.append(
                Reading(
                    ts_utc=datetime.fromisoformat(ts),
                    sensor_id=sid,
                    value=float(val),
                    unit=unit,
                    ok=bool(ok),
                    error=err,
                )
            )
        return list(reversed(out))

    async def query_actions(self, start_ts: str, end_ts: str, limit: int) -> List[ActionEvent]:
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                SELECT ts_utc,actuator_id,state,reason,avg_lux,min_lux,max_lux,window_label
                FROM actions
                WHERE ts_utc >= ? AND ts_utc <= ?
                ORDER BY ts_utc DESC
                LIMIT ?
                """,
                (start_ts, end_ts, limit),
            )
            rows = await cur.fetchall()
        out: list[ActionEvent] = []
        for ts, aid, st, reason, avg, mn, mx, lbl in rows:
            out.append(
                ActionEvent(
                    ts_utc=datetime.fromisoformat(ts),
                    actuator_id=aid,
                    state=bool(st),
                    reason=reason,
                    avg_lux=avg,
                    min_lux=mn,
                    max_lux=mx,
                    window_label=lbl,
                )
            )
        return list(reversed(out))

    async def get_all_settings(self) -> Dict[str, str]:
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute("SELECT key, value FROM settings")
            rows = await cur.fetchall()
        return {k: v for k, v in rows}

    async def set_settings_batch(self, updates: Dict[str, str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._path) as db:
            for key, value in updates.items():
                await db.execute(
                    "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (key, value, now),
                )
            await db.commit()
