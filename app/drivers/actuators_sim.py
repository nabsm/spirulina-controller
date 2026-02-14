from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class SimulatedLightActuator:
    actuator_id = "light_sim_01"

    def __init__(self) -> None:
        self._state = False

    async def get_state(self) -> bool:
        return self._state

    async def set_state(self, on: bool, reason: str) -> None:
        self._state = bool(on)
        logger.info("LIGHT set_state=%s reason=%s", self._state, reason)
