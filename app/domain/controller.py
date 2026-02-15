from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from .models import ControlDecision, Thresholds
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ControllerState:
    enabled: bool = True
    override_active: bool = False
    override_state: Optional[bool] = None
    override_until_utc: Optional[datetime] = None
    last_switch_utc: Optional[datetime] = None
    last_avg_lux: Optional[float] = None
    last_thresholds: Optional[Thresholds] = None


class LuxController:
    def __init__(self) -> None:
        self.state = ControllerState()

    def enable(self) -> None:
        self.state.enabled = True

    def disable(self) -> None:
        self.state.enabled = False

    def set_override(self, on: bool, until_utc: datetime) -> None:
        self.state.override_active = True
        self.state.override_state = on
        self.state.override_until_utc = until_utc

    def cancel_override(self) -> None:
        self.state.override_active = False
        self.state.override_state = None
        self.state.override_until_utc = None

    def _override_valid(self, now_utc: datetime) -> bool:
        if not self.state.override_active or not self.state.override_until_utc:
            return False
        if now_utc >= self.state.override_until_utc:
            self.cancel_override()
            return False
        return True

    def decide(
        self,
        now_utc: datetime,
        avg_lux: Optional[float],
        thresholds: Optional[Thresholds],
        current_light_state: bool,
        sensor_ok: bool,
    ) -> ControlDecision:
        self.state.last_avg_lux = avg_lux
        self.state.last_thresholds = thresholds

        if not self.state.enabled:
            return ControlDecision("BLOCKED", "Controller disabled", thresholds, avg_lux)

        # Manual override takes priority
        if self._override_valid(now_utc):
            desired = bool(self.state.override_state)
            action = "ON" if desired else "OFF"
            return ControlDecision(action, "Manual override", thresholds, avg_lux)

        if not sensor_ok or avg_lux is None:
            # Fail-safe choice
            desired = settings.fail_safe_light_state
            action = "ON" if desired else "OFF"
            return ControlDecision(action, "Sensor fault (fail-safe)", thresholds, avg_lux)

        # If outside schedule, do NOOP (or you could force OFF; your call)
        if thresholds is None:
            return ControlDecision("NOOP", "Outside control window", None, avg_lux)

        # Anti-chatter: min switch interval
        if self.state.last_switch_utc:
            if (now_utc - self.state.last_switch_utc) < timedelta(seconds=settings.min_switch_interval_seconds):
                return ControlDecision("NOOP", "Min switch interval not met", thresholds, avg_lux)

        # Hysteresis around thresholds
        h = settings.hysteresis_lux
        min_on = thresholds.min_lux
        max_off = thresholds.max_lux

        logger.info(
            "decide: avg=%.1f light=%s min=%.0f max=%.0f hys=%.0f "
            "→ ON_if<%.0f OFF_if>%.0f",
            avg_lux, "ON" if current_light_state else "OFF",
            min_on, max_off, h,
            min_on - h, max_off + h,
        )

        if avg_lux < (min_on - h) and not current_light_state:
            decision = ControlDecision("ON", f"Avg lux {avg_lux:.1f} below min-hys ({min_on - h:.0f})", thresholds, avg_lux)
            logger.info("decision: %s — %s", decision.action, decision.reason)
            return decision

        if avg_lux > (max_off + h) and current_light_state:
            decision = ControlDecision("OFF", f"Avg lux {avg_lux:.1f} above max+hys ({max_off + h:.0f})", thresholds, avg_lux)
            logger.info("decision: %s — %s", decision.action, decision.reason)
            return decision

        reason = (
            f"Within band (avg={avg_lux:.1f}, light={'ON' if current_light_state else 'OFF'}, "
            f"ON_if<{min_on - h:.0f}, OFF_if>{max_off + h:.0f})"
        )
        logger.info("decision: NOOP — %s", reason)
        return ControlDecision("NOOP", reason, thresholds, avg_lux)

    def mark_switched(self, now_utc: datetime) -> None:
        self.state.last_switch_utc = now_utc
