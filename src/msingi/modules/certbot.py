# ramani: src/msingi/modules/certbot.py
"""Install Certbot through snap."""

from .. import output, ssh
from ..errors import MsingiError
from ..settings import Settings
from ..ssh import Connection

NAME = "certbot"
TITLE = "Certbot"
SYSTEM = True


def setup(conn: Connection, settings: Settings) -> None:
    """Install the Certbot snap and link it to ``/usr/bin/certbot``.

    Needs snapd, which the packages module installs.

    Examples::

        setup(conn, settings)  # ✅ Certbot installed successfully
    """
    if not ssh.command_exists(conn, "snap", sudo=True):
        raise MsingiError("snapd is not installed (run the packages module first)")

    if ssh.succeeds(conn, ["snap", "list", "certbot"], sudo=True):
        output.ok("Certbot already installed")
        return

    ssh.run(conn, ["snap", "install", "core"], sudo=True, stream=True)
    ssh.run(conn, ["snap", "refresh", "core"], sudo=True, stream=True)
    remove_apt_certbot(conn)
    ssh.run(conn, ["snap", "install", "--classic", "certbot"], sudo=True, stream=True)
    ssh.run(conn, ["ln", "-sf", "/snap/bin/certbot", "/usr/bin/certbot"], sudo=True)
    output.ok("Certbot installed successfully")


def remove_apt_certbot(conn: Connection) -> None:
    """Remove the apt build of Certbot, which would clash with the snap."""
    command = [
        "env",
        "DEBIAN_FRONTEND=noninteractive",
        "apt-get",
        "remove",
        "-y",
        "certbot",
    ]
    ssh.run(conn, command, sudo=True, check=False)
