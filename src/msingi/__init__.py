# ramani: src/msingi/__init__.py
"""msingi (Swahili for "foundation"): lay the foundation of an Ubuntu server over SSH."""

from .cli import main
from .runner import provision
from .settings import Settings

__all__ = ["Settings", "main", "provision"]
