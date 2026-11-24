# ramani: src/msingi/modules/packages.py
"""Install the everyday development packages."""

from .. import output, system
from ..settings import Settings
from ..ssh import Connection

NAME = "packages"
TITLE = "necessary packages"
SYSTEM = True

PACKAGES = (
    "git",
    "curl",
    "wget",
    "snapd",
    "libsqlite3-dev",
    "sqlite3",
    "pandoc",
    "texlive-xetex",
    "build-essential",
    "software-properties-common",
)


def setup(conn: Connection, settings: Settings) -> None:
    """Install every package in ``PACKAGES`` (apt skips the ones already present).

    Examples::

        setup(conn, settings)  # ✅ All packages installed successfully
    """
    system.apt_install(conn, *PACKAGES)
    output.ok("All packages installed successfully")
