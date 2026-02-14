from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def discover_sonoff_devices(timeout: float = 3.0) -> list[dict[str, Any]]:
    """Browse mDNS for Sonoff eWeLink DIY-mode devices.

    Returns a list of dicts: {id, ip, port, hostname, type}.
    Gracefully returns [] if zeroconf is not installed.
    """
    try:
        from zeroconf import ServiceStateChange
        from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf
    except ImportError:
        logger.warning("zeroconf library not installed — mDNS discovery unavailable")
        return []

    devices: list[dict[str, Any]] = []
    found_names: set[str] = set()
    zc = AsyncZeroconf()

    def on_state_change(
        zeroconf: Any, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        if state_change is ServiceStateChange.Added:
            found_names.add(name)

    browser = AsyncServiceBrowser(
        zc.zeroconf, "_ewelink._tcp.local.", handlers=[on_state_change]
    )

    await asyncio.sleep(timeout)

    for name in found_names:
        info = await zc.zeroconf.async_get_service_info("_ewelink._tcp.local.", name)
        if info is None:
            continue
        addresses = info.parsed_addresses()
        ip = addresses[0] if addresses else None
        txt: dict[str, str] = {}
        if info.properties:
            for k, v in info.properties.items():
                key = k.decode() if isinstance(k, bytes) else str(k)
                val = v.decode() if isinstance(v, bytes) else str(v)
                txt[key] = val
        devices.append({
            "id": txt.get("id", ""),
            "ip": ip,
            "port": info.port,
            "hostname": info.server,
            "type": txt.get("type", ""),
            "txt": txt,
        })

    await browser.async_cancel()
    await zc.async_close()

    logger.info("mDNS discovery found %d Sonoff device(s)", len(devices))
    return devices
