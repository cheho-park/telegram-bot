"""Leaderboard business logic (no Telegram dependencies)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .. import db


@dataclass
class LeaderboardResult:
    status: Literal["ok", "empty", "error"]
    error_message: str | None = None
    rows: list[dict] | None = None


def _extract_data(res: Any) -> Any:
    return res.get("data") if isinstance(res, dict) else getattr(res, "data", None)


async def get_leaderboard(limit: int = 10) -> LeaderboardResult:
    try:
        res = await db.get_leaderboard(limit=limit)
    except Exception as e:
        return LeaderboardResult(
            status="error",
            error_message=f"리더보드 조회 중 오류가 발생했습니다: {e}",
        )

    data = _extract_data(res)
    if not data:
        return LeaderboardResult(status="empty", rows=[])

    return LeaderboardResult(status="ok", rows=list(data))
