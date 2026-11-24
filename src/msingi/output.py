# ramani: src/msingi/output.py
"""Status lines for the terminal; colour only in a terminal, and NO_COLOR turns it off."""

import os
import sys
from typing import TextIO

CODES = {"red": "31", "green": "32", "yellow": "33", "blue": "34", "cyan": "36"}


def paint(text: str, color: str, stream: TextIO | None = None) -> str:
    """Colour ``text`` when ``stream`` (default: stdout) is a terminal.

    Examples::

        paint("done", "green")  # "\\x1b[32mdone\\x1b[0m" in a terminal
        paint("done", "green")  # "done" when piped
    """
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") or not stream.isatty():
        return text
    return f"\033[{CODES[color]}m{text}\033[0m"


def step(text: str) -> None:
    """Announce what is about to happen.

    Examples::

        step("🚀 Setting up Nginx...")  # 🚀 Setting up Nginx...
    """
    print(paint(text, "blue"), flush=True)


def ok(text: str) -> None:
    """Report something done or already in place.

    Examples::

        ok("Nginx is running")  # ✅ Nginx is running
    """
    print(paint(f"✅ {text}", "green"), flush=True)


def warn(text: str) -> None:
    """Report a problem that does not stop the run.

    Examples::

        warn("Failed to install ufw")  # ⚠️  Failed to install ufw
    """
    print(paint(f"⚠️  {text}", "yellow"), flush=True)


def note(text: str) -> None:
    """Share a hint.

    Examples::

        note("Run `uv python install` later")  # ℹ️  Run `uv python install` later
    """
    print(paint(f"ℹ️  {text}", "blue"), flush=True)


def dry(text: str) -> None:
    """Say what a real run would do.

    Examples::

        dry("install necessary packages")  # [DRY RUN] Would install necessary packages
    """
    print(paint(f"[DRY RUN] Would {text}", "cyan"), flush=True)


def fail(text: str) -> None:
    """Report an error on stderr.

    Examples::

        fail("msingi: no modules selected")  # ❌ msingi: no modules selected
    """
    print(paint(f"❌ {text}", "red", sys.stderr), file=sys.stderr, flush=True)
