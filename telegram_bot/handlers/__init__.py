"""Handler package for modular Telegram handlers."""
from . import core
from . import weather
from . import fortune
from . import attendance
from . import profile
from . import on_message

__all__ = [
    "core",
    "weather",
    "fortune",
    "attendance",
    "profile",
    "on_message",
]
