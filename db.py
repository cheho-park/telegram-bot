"""Simple Supabase helper (sync client wrapped for async handlers).

This module expects `SUPABASE_URL` and `SUPABASE_KEY` to be set in the environment
(you can load them via `python-dotenv` in your main script).

It provides two coroutine functions used by the bot:
- create_user(user_id: int, username: str|None)
- get_user(user_id: int)

Notes:
- Uses `asyncio.to_thread` to run the (sync) supabase client in a thread so it
  can be called from async handlers.
"""
import os
import asyncio
from typing import Optional, Any, Dict
import datetime
from datetime import timezone

from supabase import create_client

_client = None


def _init_client():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set in environment")
        _client = create_client(url, key)
    return _client


async def create_user(user_id: int, username: Optional[str]) -> Dict[str, Any]:
    def _sync():
        client = _init_client()
        # Assumes a table `users` exists with at least columns: id (bigint / text) and username
        return client.table("users").insert({"id": user_id, "username": username}).execute()

    return await asyncio.to_thread(_sync)


async def get_user(user_id: int) -> Dict[str, Any]:
    def _sync():
        client = _init_client()
        return client.table("users").select("*").eq("id", user_id).limit(1).execute()

    return await asyncio.to_thread(_sync)


async def record_attendance(user_id: int) -> Dict[str, Any]:
    def _sync():
        client = _init_client()
        # Assumes a table `attendances` exists with columns: id (serial), user_id (bigint), ts (timestamptz)
        return client.table("attendances").insert({"user_id": user_id}).execute()

    return await asyncio.to_thread(_sync)


async def get_attendance(user_id: int, limit: int = 30) -> Dict[str, Any]:
    def _sync():
        client = _init_client()
        return (
            client.table("attendances")
            .select("*")
            .eq("user_id", user_id)
            .order("ts", desc=True)
            .limit(limit)
            .execute()
        )

    return await asyncio.to_thread(_sync)


async def attended_today(user_id: int) -> bool:
    """Return True if user has an attendance record for today (UTC).

    Uses UTC day boundaries for simplicity; adjust if you need local timezone.
    """
    def _sync():
        client = _init_client()
        now = datetime.datetime.now(timezone.utc)
        start_of_day = datetime.datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        # Supabase expects RFC3339 timestamps
        start_iso = start_of_day.isoformat()
        res = (
            client.table("attendances")
            .select("id")
            .eq("user_id", user_id)
            .gte("ts", start_iso)
            .limit(1)
            .execute()
        )
        # res may be a dict or object with .data
        data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
        return bool(data)

    return await asyncio.to_thread(_sync)
