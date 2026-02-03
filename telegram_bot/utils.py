"""Utility helpers for formatting timestamps, leaderboard text, XP progress, etc."""
from __future__ import annotations
import datetime
from datetime import timezone
from typing import Any, Dict, Iterable, List


KST = datetime.timezone(datetime.timedelta(hours=9))


def extract_ttl_from_args(args: List[str]) -> float | None:
    """Extract ttl value from command arguments like ['ttl:3'].
    
    Returns ttl value in seconds if found, otherwise None.
    """
    if not args:
        return None
    for arg in args:
        if isinstance(arg, str) and arg.startswith("ttl:"):
            try:
                return float(arg[4:])
            except (ValueError, IndexError):
                pass
    return None


def parse_iso_to_kst(iso: str) -> datetime.datetime:
    """Parse an ISO timestamp and return it as a KST-aware datetime."""
    if iso is None:
        raise ValueError("iso timestamp is None")
    if isinstance(iso, str) and iso.endswith("Z"):
        iso = iso.replace("Z", "+00:00")
    dt = datetime.datetime.fromisoformat(iso)
    return dt.astimezone(KST)


def format_ts_kst(iso: str | None) -> str:
    """Return a nicely formatted KST timestamp (YYYY-MM-DD HH:MM KST)."""
    if not iso:
        return "-"
    try:
        dt = parse_iso_to_kst(iso)
    except Exception:
        return str(iso)
    return dt.strftime("%Y-%m-%d %H:%M:%S KST")


def format_username(username: str | None, user_id: int | str | None = None) -> str:
    if username:
        return f"@{username}"
    return f"ID:{user_id}"


def format_xp_progress(xp: int, level: int, next_level_xp: int) -> str:
    prev_xp = 100 * (level - 1) * (level - 1)
    total_needed = max(next_level_xp - prev_xp, 1)
    gained = max(xp - prev_xp, 0)
    percent = int(100 * gained / total_needed) if total_needed else 0
    return f"Lv{level} — {xp} XP ({gained}/{total_needed} | {percent}%)"


def format_leaderboard(rows: Iterable[Dict[str, Any]]) -> str:
    """Rows should include id, username, xp, level; returns formatted text with medals for top 3."""
    medals = ["🥇", "🥈", "🥉"]
    lines: List[str] = []
    # calculate column widths
    items = list(rows)
    name_len = max((len(str(r.get("username") or r.get("id"))) for r in items), default=7)
    xp_len = max((len(str(r.get("xp", 0))) for r in items), default=3)
    for i, row in enumerate(items, start=1):
        name = (row.get("username") or row.get("id"))
        xp = row.get("xp", 0)
        lvl = row.get("level", 1)
        medal = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"{medal} {str(name):{name_len}} — Lv{lvl:>2} — {xp:>{xp_len}} XP")
    return "\n".join(lines)


__all__ = [
    "KST",
    "extract_ttl_from_args",
    "parse_iso_to_kst",
    "format_ts_kst",
    "format_username",
    "format_xp_progress",
    "format_leaderboard",
]
