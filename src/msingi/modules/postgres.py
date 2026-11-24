# ramani: src/msingi/modules/postgres.py
"""Install PostgreSQL and keep its service running."""

from .. import output, ssh, system
from ..settings import Settings
from ..ssh import Connection

NAME = "postgres"
TITLE = "PostgreSQL"
SYSTEM = True


def setup(conn: Connection, settings: Settings) -> None:
    """Install PostgreSQL (plus contrib and libpq), then enable and start the service.

    Examples::

        setup(conn, settings)  # ✅ PostgreSQL is running
    """
    if ssh.command_exists(conn, "psql", sudo=True):
        output.ok("PostgreSQL already installed")
    else:
        system.apt_install(conn, "postgresql", "postgresql-contrib", "libpq-dev")

    system.enable_and_start(conn, "postgresql")
    output.ok("PostgreSQL is running")
