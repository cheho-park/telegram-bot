"""Main handler module (migrated into a package for modular handlers)."""
from . import weather

# Re-export common handlers for legacy imports
from .core import *
