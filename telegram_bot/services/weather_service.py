"""Weather service: async OpenWeather API access, parsing and caching.

This module provides an async interface to query OpenWeather, parse the response
and caches the result to avoid excessive API calls.
"""
from __future__ import annotations
import asyncio
import logging
import os
import time
from typing import Any, Optional, Tuple

import httpx

from ..utils import KST

WEATHER_TOKEN = os.getenv("OPENWEATHER_TOKEN")
if not WEATHER_TOKEN:
    logging.warning("OPENWEATHER_TOKEN not set in environment; weather service disabled")

_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()

# Simple TTL cache: key -> (data, expires_at)
_cache: dict[str, tuple[Any, float]] = {}
_cache_lock = asyncio.Lock()
_CACHE_TTL = 300  # seconds


async def _get_client() -> httpx.AsyncClient:
    global _client
    async with _client_lock:
        if _client is None:
            _client = httpx.AsyncClient(timeout=5.0)
        return _client


def _cache_key(city_api_name: str) -> str:
    return city_api_name.lower()


async def _get_cached(city_api_name: str) -> Optional[Any]:
    key = _cache_key(city_api_name)
    now = time.time()
    async with _cache_lock:
        item = _cache.get(key)
        if item and item[1] > now:
            return item[0]
        if item:
            _cache.pop(key, None)
    return None


async def _set_cache(city_api_name: str, data: Any) -> None:
    key = _cache_key(city_api_name)
    async with _cache_lock:
        _cache[key] = (data, time.time() + _CACHE_TTL)


async def get_weather_raw(city_api_name: str) -> Optional[dict]:
    """Fetch raw weather data from OpenWeather asynchronously with caching.

    Returns the JSON dict or None.
    """
    if not WEATHER_TOKEN:
        return None

    cached = await _get_cached(city_api_name)
    if cached is not None:
        logging.debug("Weather cache hit: %s", city_api_name)
        return cached

    client = await _get_client()
    url = (
        f"https://api.openweathermap.org/data/2.5/weather?q={city_api_name},KR"
        f"&appid={WEATHER_TOKEN}&units=metric&lang=kr"
    )
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        # cache the raw response
        await _set_cache(city_api_name, data)
        return data
    except Exception as e:
        logging.exception("Weather API error for %s: %s", city_api_name, e)
        return None


def parse_weather_data(data: dict) -> Optional[Tuple[str, float, int, float]]:
    try:
        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"].get("speed", 0.0)
        return weather, float(temp), int(humidity), float(wind_speed)
    except Exception:
        return None


async def close_client() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None
