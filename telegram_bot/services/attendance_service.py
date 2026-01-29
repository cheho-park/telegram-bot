"""Attendance service that wraps DB call with additional logic like awarding XP."""
from __future__ import annotations
import asyncio
from typing import Any

from .. import db


async def attend_and_award(user_id: int, xp_amount: int = 10) -> dict[str, Any]:
    # record attendance
    await db.record_attendance(user_id)
    # award xp synchronously and return resulting info
    res = await db.add_xp(user_id, xp_amount)
    return res
