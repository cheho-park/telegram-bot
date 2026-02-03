"""Attendance-related business logic (no Telegram dependencies)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal

from .. import db


@dataclass
class AttendanceResult:
    status: Literal["already", "recorded", "error"]
    error_message: str | None = None
    should_notify: bool = False
    level_up: bool = False
    old_level: int | None = None
    new_level: int | None = None


@dataclass
class AttendanceHistoryResult:
    status: Literal["ok", "empty", "error"]
    error_message: str | None = None
    timestamps: list[str] | None = None


@dataclass
class StreakResult:
    status: Literal["ok", "error"]
    error_message: str | None = None
    streak: int = 0


def _extract_data(res: Any) -> Any:
    return res.get("data") if isinstance(res, dict) else getattr(res, "data", None)


def _extract_level_info(data: Any) -> tuple[bool, int | None, int | None]:
    if not isinstance(data, dict):
        return False, None, None
    old_level = data.get("old_level")
    new_level = data.get("new_level")
    if old_level and new_level and new_level > old_level:
        return True, int(old_level), int(new_level)
    return False, old_level, new_level


async def attend(user_id: int) -> AttendanceResult:
    try:
        already = await db.attended_today(user_id)
    except Exception as e:
        return AttendanceResult(
            status="error",
            error_message=f"출석 확인 중 오류가 발생했습니다: {e}",
        )

    if already:
        return AttendanceResult(status="already")

    try:
        res = await db.record_attendance(user_id)
    except Exception as e:
        return AttendanceResult(
            status="error",
            error_message=f"출석 처리 중 오류가 발생했습니다: {e}",
        )

    data = _extract_data(res)
    level_up, old_level, new_level = _extract_level_info(data)
    return AttendanceResult(
        status="recorded",
        should_notify=bool(data),
        level_up=level_up,
        old_level=old_level,
        new_level=new_level,
    )


async def get_attendance_history(user_id: int, limit: int = 30) -> AttendanceHistoryResult:
    try:
        res = await db.get_attendance(user_id, limit=limit)
    except Exception as e:
        return AttendanceHistoryResult(
            status="error",
            error_message=f"출석 기록 조회 중 오류가 발생했습니다: {e}",
        )

    data = _extract_data(res)
    if not data:
        return AttendanceHistoryResult(status="empty", timestamps=[])

    timestamps: list[str] = []
    for row in data:
        ts = row.get("ts") if isinstance(row, dict) else getattr(row, "ts", None)
        if ts:
            timestamps.append(ts)

    if not timestamps:
        return AttendanceHistoryResult(status="empty", timestamps=[])

    return AttendanceHistoryResult(status="ok", timestamps=timestamps)


async def get_streak(user_id: int) -> StreakResult:
    try:
        s = await db.get_streak(user_id)
    except Exception as e:
        return StreakResult(
            status="error",
            error_message=f"연속 출석 조회 중 오류가 발생했습니다: {e}",
        )
    return StreakResult(status="ok", streak=s)
