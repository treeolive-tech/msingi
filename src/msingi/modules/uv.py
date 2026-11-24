# ramani: src/msingi/modules/uv.py
"""Install uv for the target user, then a Python through it."""

from .. import output, ssh
from ..settings import Settings
from ..ssh import Connection

NAME = "uv"
TITLE = "uv"
SYSTEM = False

UV_BIN = '"$HOME/.local/bin/uv"'
MANUAL_HINT = "You can install Python manually after restarting your shell with: uv python install"


def setup(conn: Connection, settings: Settings) -> None:
    """Install uv, then install a Python if uv doesn't manage one yet.

    Examples::

        setup(user_conn, settings)  # ✅ Python installed successfully with uv
    """
    install_uv(conn)
    install_python(conn)


def install_uv(conn: Connection) -> None:
    """Install uv with its official installer unless ``~/.local/bin/uv`` exists."""
    if ssh.succeeds(conn, f"test -x {UV_BIN}"):
        output.ok("uv already installed")
        return
    ssh.run(
        conn,
        "set -o pipefail; curl -LsSf https://astral.sh/uv/install.sh | sh",
        stream=True,
    )


def install_python(conn: Connection) -> None:
    """Install Python through uv unless uv already manages one (a failure only warns).

    ``--managed-python`` leaves out the system Python, which Ubuntu always has.

    Examples::

        install_python(conn)  # ✅ Python already installed with uv
    """
    listing = f"{UV_BIN} python list --only-installed --managed-python"
    installed = ssh.run(conn, listing, check=False).stdout
    if "cpython" in installed:
        output.ok("Python already installed with uv")
        return

    result = ssh.run(conn, f"{UV_BIN} python install", check=False, stream=True)
    if result.returncode == 0:
        output.ok("Python installed successfully with uv")
    else:
        output.note(MANUAL_HINT)
