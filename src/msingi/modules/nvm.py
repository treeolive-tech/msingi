# ramani: src/msingi/modules/nvm.py
"""Install nvm for the target user, then the latest Node.js."""

from .. import output, ssh
from ..settings import Settings
from ..ssh import Connection

NAME = "nvm"
TITLE = "nvm"
SYSTEM = False

LOAD_NVM = 'export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; '
MANUAL_HINT = "You can install Node.js manually after restarting your shell with: nvm install node"


def setup(conn: Connection, settings: Settings) -> None:
    """Install nvm (the version in ``settings.nvm_version``), then Node.js.

    Examples::

        setup(user_conn, settings)  # ✅ Node.js installed successfully with nvm
    """
    install_nvm(conn, settings.nvm_version)
    if not ssh.succeeds(conn, 'test -s "$HOME/.nvm/nvm.sh"'):
        output.warn("nvm.sh not found")
        output.note(MANUAL_HINT)
        return
    install_node(conn)


def install_nvm(conn: Connection, version: str) -> None:
    """Install nvm with its official script unless ``~/.nvm`` exists."""
    if ssh.succeeds(conn, 'test -d "$HOME/.nvm"'):
        output.ok("nvm already installed")
        return
    url = f"https://raw.githubusercontent.com/nvm-sh/nvm/{version}/install.sh"
    ssh.run(conn, f"set -o pipefail; curl -o- {url} | bash", stream=True)


def install_node(conn: Connection) -> None:
    """Install the latest Node.js unless nvm already has one, then update npm.

    ``nvm version node`` prints ``N/A`` when no Node.js is installed.

    Examples::

        install_node(conn)  # ✅ Node.js already installed with nvm
    """
    current = ssh.run(conn, LOAD_NVM + "nvm version node", check=False).stdout.strip()
    if current not in ("", "N/A"):
        output.ok("Node.js already installed with nvm")
        return

    output.step("Installing Node.js with nvm...")
    result = ssh.run(conn, LOAD_NVM + "nvm install node", check=False, stream=True)
    if result.returncode != 0:
        output.warn("Failed to install Node.js in this session")
        output.note(MANUAL_HINT)
        return
    output.ok("Node.js installed successfully with nvm")

    if ssh.succeeds(conn, LOAD_NVM + "npm install -g npm@latest"):
        output.ok("npm updated successfully")
