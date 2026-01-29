"""Supabase DB helpers (moved into package for modularity)."""
import os
import asyncio
import datetime
from datetime import timezone
from typing import Optional, Any
import math
import threading
import time

from supabase import create_client

_client = None

# simple in-process cache for user rows keyed by user_id
_user_cache: dict[int, tuple[dict, float]] = {}
# cache TTL seconds for user info; small value reduces stale data
_USER_CACHE_TTL = 5.0
_cache_lock = threading.Lock()
_leaderboard_cache: dict[int, tuple[Any, float]] = {}
_LEADERBOARD_CACHE_TTL = 3.0


def _init_client():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set in environment")
        _client = create_client(url, key)
    return _client


def _cache_get(user_id: int) -> Optional[dict]:
    now = time.time()
    with _cache_lock:
        entry = _user_cache.get(user_id)
        if not entry:
            return None
        data, expires = entry
        if expires < now:
            _user_cache.pop(user_id, None)
            return None
        return data


def _cache_set(user_id: int, data: dict) -> None:
    now = time.time()
    with _cache_lock:
        _user_cache[user_id] = (data, now + _USER_CACHE_TTL)


def _cache_invalidate(user_id: int) -> None:
    with _cache_lock:
        _user_cache.pop(user_id, None)
    # also invalidate leaderboard caches
    with _cache_lock:
        _leaderboard_cache.clear()


def _now_kst_iso() -> str:
    # Return current time in KST as ISO string
    kst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(kst).isoformat()


async def create_user(user_id: int, username: Optional[str]) -> Any:
    def _sync():
        client = _init_client()
        # Try insert with default xp/level. If duplicate key (user already exists),
        # return the existing user row instead of propagating the error.
        res = client.table("users").insert({"id": user_id, "username": username, "xp": 0, "level": 1, "last_xp_at": None}).execute()

        # Supabase client may return an object/dict with an 'error' key on failure.
        err = None
        if isinstance(res, dict):
            err = res.get("error")
        else:
            # Some client versions return objects with .error
            err = getattr(res, "error", None)

        if err:
            # If duplicate key (Postgres code 23505), fetch and return existing user
            code = None
            if isinstance(err, dict):
                code = err.get("code")
            else:
                code = getattr(err, "code", None)

            if code == "23505":
                # return existing user row
                existing = client.table("users").select("*").eq("id", user_id).limit(1).execute()
                # cache existing
                data = existing.get("data") if isinstance(existing, dict) else getattr(existing, "data", None)
                if data:
                    _cache_set(user_id, data[0] if isinstance(data, (list, tuple)) and data else data)
                return existing
            # otherwise return the original response (propagate error to caller)
            return res

        # success: cache initial user row
        row = {"id": user_id, "username": username, "xp": 0, "level": 1, "last_xp_at": None}
        _cache_set(user_id, row)
        return res

    return await asyncio.to_thread(_sync)


async def get_user(user_id: int) -> Any:
    def _sync():
        client = _init_client()
        return client.table("users").select("*").eq("id", user_id).limit(1).execute()

    return await asyncio.to_thread(_sync)


async def record_attendance(user_id: int) -> Any:
    def _sync():
        client = _init_client()
        return client.table("attendances").insert({"user_id": user_id}).execute()

    return await asyncio.to_thread(_sync)


async def get_attendance(user_id: int, limit: int = 30) -> Any:
    def _sync():
        client = _init_client()
        return (
            client.table("attendances").select("*").eq("user_id", user_id).order("ts", desc=True).limit(limit).execute()
        )

    return await asyncio.to_thread(_sync)


async def attended_today(user_id: int) -> bool:
    def _sync():
        client = _init_client()
        # Use KST for day boundaries
        kst = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(kst)
        start_of_day = datetime.datetime(now.year, now.month, now.day, tzinfo=kst)
        start_iso = start_of_day.isoformat()
        res = (
            client.table("attendances").select("id").eq("user_id", user_id).gte("ts", start_iso).limit(1).execute()
        )
        data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
        return bool(data)

    return await asyncio.to_thread(_sync)


async def get_streak(user_id: int, max_days: int = 365) -> int:
    """Return the current consecutive attendance streak ending at the most recent attendance.

    The streak is computed from the most recent attendance date backward counting
    consecutive calendar days (UTC). If the user has no attendance records, returns 0.
    """
    from datetime import timedelta

    def _sync():
        client = _init_client()
        # fetch recent attendance timestamps (limit to max_days records)
        res = (
            client.table("attendances")
            .select("ts")
            .eq("user_id", user_id)
            .order("ts", desc=True)
            .limit(max_days)
            .execute()
        )
        return res

    res = await asyncio.to_thread(_sync)
    data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if not data:
        return 0

    # Parse timestamps to KST dates (unique)
    dates = []
    for row in data:
        ts = row.get("ts") if isinstance(row, dict) else getattr(row, "ts", None)
        if not ts:
            continue
        # Normalize ISO string that may end with Z
        if isinstance(ts, str) and ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        try:
            dt = datetime.datetime.fromisoformat(ts)
        except Exception:
            # skip unparsable
            continue
        # Convert to KST date
        kst = datetime.timezone(datetime.timedelta(hours=9))
        dt = dt.astimezone(kst).date()
        if not dates or dates[-1] != dt:
            dates.append(dt)

    if not dates:
        return 0

    # dates is descending-ordered unique list of dates
    streak = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] - timedelta(days=1):
            streak += 1
        else:
            break

    return streak


def calc_level_from_xp(xp: int) -> int:
    """Compute level from total XP using simple quadratic curve.

    Level formula: level = floor(sqrt(xp / 100)) + 1
    => xp required to reach level N is 100*(N-1)^2
    """
    if xp < 0:
        xp = 0
    # integer division
    base = xp // 100
    level = math.isqrt(base) + 1
    return int(level)


def _xp_for_level(level: int) -> int:
    # xp required to reach given level (total xp). Level 1 requires 0 xp; Level 2 requires 100.
    if level <= 1:
        return 0
    return 100 * (level - 1) * (level - 1)


def xp_for_level(level: int) -> int:
    return _xp_for_level(level)


async def add_xp(user_id: int, amount: int) -> Any:
    """Add XP to a user and update level if necessary.

    Returns the updated user row (as supabase response).
    """
    def _sync():
        client = _init_client()
        # get user
        row = client.table("users").select("*").eq("id", user_id).limit(1).execute()
        data = row.get("data") if isinstance(row, dict) else getattr(row, "data", None)
        if not data:
            # create user with xp amount
            new_xp = amount
            new_level = calc_level_from_xp(new_xp)
            res = client.table("users").insert({"id": user_id, "xp": new_xp, "level": new_level, "last_xp_at": datetime.datetime.now(timezone.utc).isoformat()}).execute()
            # update cache
            row = {"id": user_id, "xp": new_xp, "level": new_level, "last_xp_at": datetime.datetime.now(timezone.utc).isoformat()}
            _cache_set(user_id, row)
            return {"old_xp": 0, "old_level": 1, "new_xp": new_xp, "new_level": new_level, "res": res}

        user = data[0]
        cur_xp = user.get("xp", 0) if isinstance(user, dict) else getattr(user, "xp", 0)
        cur_level = user.get("level", 1) if isinstance(user, dict) else getattr(user, "level", 1)
        new_xp = (cur_xp or 0) + amount
        new_level = calc_level_from_xp(new_xp)
        # update
        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        res = client.table("users").update({"xp": new_xp, "level": new_level, "last_xp_at": now_iso}).eq("id", user_id).execute()
        # update cache
        row = {"id": user_id, "xp": new_xp, "level": new_level, "last_xp_at": now_iso}
        _cache_set(user_id, row)
        return {"old_xp": cur_xp or 0, "old_level": cur_level or 1, "new_xp": new_xp, "new_level": new_level, "res": res}

    return await asyncio.to_thread(_sync)


async def get_leaderboard(limit: int = 10) -> Any:
    # try leaderboard cache
    now = time.time()
    with _cache_lock:
        e = _leaderboard_cache.get(limit)
        if e and e[1] > now:
            return e[0]

    def _sync():
        client = _init_client()
        return client.table("users").select("id, username, xp, level").order("xp", desc=True).limit(limit).execute()

    res = await asyncio.to_thread(_sync)
    with _cache_lock:
        _leaderboard_cache[limit] = (res, time.time() + _LEADERBOARD_CACHE_TTL)
    return res


async def get_xp_info(user_id: int) -> dict:
    # try cache first
    cached = _cache_get(user_id)
    if cached:
        # convert to consistent shape
        return {"id": cached.get("id"), "xp": cached.get("xp", 0), "level": cached.get("level", 1), "next_xp": _xp_for_level(cached.get("level", 1) + 1), "last_xp_at": cached.get("last_xp_at")}

    def _sync():
        client = _init_client()
        return client.table("users").select("id, username, xp, level, last_xp_at").eq("id", user_id).limit(1).execute()

    res = await asyncio.to_thread(_sync)
    data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if not data:
        return {"id": user_id, "xp": 0, "level": 1, "next_xp": _xp_for_level(2), "last_xp_at": None}
    user = data[0]
    xp = user.get("xp", 0) if isinstance(user, dict) else getattr(user, "xp", 0)
    level = user.get("level", 1) if isinstance(user, dict) else getattr(user, "level", 1)
    last_xp_at = user.get("last_xp_at") if isinstance(user, dict) else getattr(user, "last_xp_at", None)
    next_level = level + 1
    next_xp = _xp_for_level(next_level)
    return {"id": user_id, "xp": xp, "level": level, "next_xp": next_xp, "last_xp_at": last_xp_at}


