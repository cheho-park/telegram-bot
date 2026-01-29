"""XP service: in-memory queue for message XP and background flush to DB.

This reduces DB write frequency and improves message path latency.
"""
from __future__ import annotations
import asyncio
import time
from typing import Dict, Optional

from .. import db


_pending: Dict[int, int] = {}
_lock = asyncio.Lock()


async def queue_xp(user_id: int, amount: int) -> None:
    async with _lock:
        _pending[user_id] = _pending.get(user_id, 0) + amount


async def flush_pending(concurrency: int = 5) -> None:
    """Flush all pending XP updates to DB. This is typically run in background.

    Concurrency controls number of parallel DB calls at a time.
    """
    async with _lock:
        items = list(_pending.items())
        _pending.clear()

    if not items:
        return

    sem = asyncio.Semaphore(concurrency)

    async def _flush_item(uid: int, amt: int):
        async with sem:
            try:
                await db.add_xp(uid, amt)
            except Exception as e:
                # If write fails, requeue
                async with _lock:
                    _pending[uid] = _pending.get(uid, 0) + amt

    await asyncio.gather(*[_flush_item(uid, amt) for uid, amt in items])


async def start_background_flush(interval_seconds: float = 2.0):
    """Start an infinite background task that flushes pending XP at interval_seconds."""
    while True:
        await asyncio.sleep(interval_seconds)
        await flush_pending()
