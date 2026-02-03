"""XP service: in-memory queue for message XP and background flush to DB.

This reduces DB write frequency and improves message path latency.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Literal

from .. import db


_pending: Dict[int, int] = {}
_lock = asyncio.Lock()

MESSAGE_XP = 5
MESSAGE_COOLDOWN_SEC = 60


@dataclass
class XpAwardResult:
    status: Literal["awarded", "skipped", "error"]
    error_message: str | None = None


async def queue_xp(user_id: int, amount: int) -> None:
    async with _lock:
        _pending[user_id] = _pending.get(user_id, 0) + amount


async def award_message_xp(user_id: int) -> XpAwardResult:
    """Award message XP for a user, respecting cooldown."""
    try:
        info = await db.get_xp_info(user_id)
    except Exception as e:
        print(
            f"[ERROR] award_message_xp: Failed to get xp info for user {user_id}: "
            f"{type(e).__name__}: {e}"
        )
        return XpAwardResult(status="error", error_message=str(e))

    last_xp = info.get("last_xp_at")
    if last_xp:
        if isinstance(last_xp, str) and last_xp.endswith("Z"):
            last_xp = last_xp.replace("Z", "+00:00")
        try:
            last_dt = datetime.fromisoformat(last_xp)
            kst = timezone(timedelta(hours=9))
            last_dt_kst = last_dt.astimezone(kst)
            now_kst = datetime.now(kst)
            if (now_kst - last_dt_kst).total_seconds() < MESSAGE_COOLDOWN_SEC:
                return XpAwardResult(status="skipped")
        except Exception:
            pass

    try:
        await queue_xp(user_id, MESSAGE_XP)
    except Exception as e:
        print(
            f"[ERROR] award_message_xp: Failed to queue xp for user {user_id}: "
            f"{type(e).__name__}: {e}"
        )
        return XpAwardResult(status="error", error_message=str(e))

    return XpAwardResult(status="awarded")


@dataclass
class XpInfoResult:
    status: Literal["ok", "error"]
    error_message: str | None = None
    xp: int = 0
    level: int = 1
    next_xp: int = 0


async def get_xp_info(user_id: int) -> XpInfoResult:
    try:
        info = await db.get_xp_info(user_id)
    except Exception as e:
        return XpInfoResult(status="error", error_message=str(e))

    return XpInfoResult(
        status="ok",
        xp=info.get("xp", 0),
        level=info.get("level", 1),
        next_xp=info.get("next_xp", 0),
    )


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
