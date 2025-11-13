"""
Utilities: health-check cache para não extrapolar 1 chamada a cada 5s.
A função cached_health_check(name, base_url) mantém cache em memória com TTL de 4s.
"""
import asyncio
import time
import httpx
from typing import Optional, Dict
import os

_health_cache: Dict[str, tuple[float, Dict]] = {}
_health_lock = asyncio.Lock()

HEALTH_TTL = float(os.getenv("HEALTH_TTL", "4.0"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "2.0"))

async def cached_health_check(name: str, base_url: str) -> Optional[Dict]:
    """Retorna JSON de health-check cacheado (ou atualiza se expirado)."""
    now = time.time()
    async with _health_lock:
        entry = _health_cache.get(name)
        if entry:
            ts, payload = entry
            if now - ts < HEALTH_TTL:
                return payload

    url = f"{base_url}/payments/service-health"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            payload = resp.json()
            async with _health_lock:
                _health_cache[name] = (time.time(), payload)
            return payload
        if resp.status_code == 429:
            return None
    except Exception:
        pass
    return None
