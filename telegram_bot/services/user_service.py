"""User/profile business logic (no Telegram dependencies)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .. import db


@dataclass
class RegisterResult:
    status: Literal["created", "exists", "error", "unknown"]
    error_message: str | None = None
    raw_result: Any | None = None


@dataclass
class ProfileResult:
    status: Literal["found", "not_found", "error"]
    error_message: str | None = None
    user_id: int | None = None
    username: str | None = None
    xp: int = 0
    level: int = 1
    next_xp: int = 0
    last_xp_at: str | None = None


def _extract_data(res: Any) -> Any:
    return res.get("data") if isinstance(res, dict) else getattr(res, "data", None)


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


async def register_user(user_id: int, username: str | None) -> RegisterResult:
    try:
        existing = await db.get_user(user_id)
    except Exception as e:
        return RegisterResult(status="error", error_message=str(e))

    existing_data = _extract_data(existing)
    if existing_data:
        return RegisterResult(status="exists")

    try:
        res = await db.create_user(user_id, username)
    except Exception as e:
        return RegisterResult(status="error", error_message=str(e))

    data = _extract_data(res)
    if data:
        return RegisterResult(status="created")

    return RegisterResult(status="unknown", raw_result=res)


async def get_profile(user_id: int) -> ProfileResult:
    try:
        res = await db.get_user(user_id)
    except Exception as e:
        return ProfileResult(status="error", error_message=str(e))

    data = _extract_data(res)
    if not data:
        return ProfileResult(status="not_found")

    row = data[0] if isinstance(data, (list, tuple)) and data else data
    xp = _row_get(row, "xp", 0)
    level = _row_get(row, "level", 1)
    next_xp = db.xp_for_level((level or 1) + 1)

    return ProfileResult(
        status="found",
        user_id=_row_get(row, "id", user_id),
        username=_row_get(row, "username", None),
        xp=xp or 0,
        level=level or 1,
        next_xp=next_xp,
        last_xp_at=_row_get(row, "last_xp_at", None),
    )
