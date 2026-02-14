from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class SonoffBasicR3Actuator:
    """Actuator driver for Sonoff BASICR3 in eWeLink DIY mode."""

    actuator_id = "sonoff_basicr3"

    def __init__(
        self,
        ip: str = "192.168.1.19",
        port: int = 8081,
        device_id: str = "1000b8d61a",
        timeout: float = 5.0,
    ) -> None:
        self._base_url = f"http://{ip}:{port}"
        self._device_id = device_id
        self._timeout = timeout
        self._last_known_state: bool = False

    async def get_state(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/zeroconf/info",
                    json={"deviceid": self._device_id, "data": {}},
                )
                resp.raise_for_status()
                data = resp.json()
                switch_val = data["data"]["switch"]
                self._last_known_state = switch_val == "on"
        except Exception:
            logger.warning(
                "Sonoff get_state failed, returning last known state: %s",
                self._last_known_state,
                exc_info=True,
            )
        return self._last_known_state

    async def set_state(self, on: bool, reason: str) -> None:
        switch_val = "on" if on else "off"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/zeroconf/switch",
                    json={
                        "deviceid": self._device_id,
                        "data": {"switch": switch_val},
                    },
                )
                resp.raise_for_status()
                self._last_known_state = on
                logger.info("Sonoff set_state=%s reason=%s", switch_val, reason)
        except Exception:
            logger.warning(
                "Sonoff set_state(%s) failed, reason=%s",
                switch_val,
                reason,
                exc_info=True,
            )
