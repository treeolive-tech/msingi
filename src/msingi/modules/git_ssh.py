# ramani: src/msingi/modules/git_ssh.py
"""Set the global Git identity and create an SSH key to give to GitHub or GitLab."""

import shlex

from .. import output, ssh
from ..errors import MsingiError
from ..settings import Settings
from ..ssh import Connection

NAME = "git-ssh"
TITLE = "Git and SSH"
SYSTEM = False

KEY_PATH = "$HOME/.ssh/id_ed25519"


def setup(conn: Connection, settings: Settings) -> None:
    """Configure Git, make ``~/.ssh``, create the key if absent, and make the SSH config.

    Examples::

        setup(user_conn, settings)  # ✅ Generated new SSH key
    """
    for tool in ("git", "ssh-keygen"):
        if not ssh.command_exists(conn, tool):
            raise MsingiError(f"{tool} command not found")

    configure_git(conn, settings.git_user_name, settings.git_user_email)
    ssh.run(conn, 'mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"')
    create_key(conn, settings.git_user_email)
    create_config(conn)


def configure_git(conn: Connection, name: str, email: str) -> None:
    """Set the global Git name and email (safe to repeat).

    Examples::

        configure_git(conn, "Ada Lovelace", "ada@example.com")
    """
    ssh.run(conn, ["git", "config", "--global", "user.name", name])
    ssh.run(conn, ["git", "config", "--global", "user.email", email])
    output.ok(f"Git configured with name: {name}")
    output.ok(f"Git configured with email: {email}")


def create_key(conn: Connection, email: str) -> None:
    """Generate an ed25519 key without a passphrase unless one exists.

    Examples::

        create_key(conn, "ada@example.com")  # ✅ SSH key already exists
    """
    if ssh.succeeds(conn, f'test -f "{KEY_PATH}"'):
        output.ok("SSH key already exists")
        return

    output.warn("Generating new SSH key...")
    ssh.run(conn, f'ssh-keygen -t ed25519 -C {shlex.quote(email)} -N "" -f "{KEY_PATH}"')
    ssh.run(conn, f'chmod 600 "{KEY_PATH}" && chmod 644 "{KEY_PATH}.pub"')
    output.ok("Generated new SSH key")


def create_config(conn: Connection) -> None:
    """Create an empty ``~/.ssh/config`` unless it exists."""
    config = '"$HOME/.ssh/config"'
    if not ssh.succeeds(conn, f"test -f {config}"):
        ssh.run(conn, f"touch {config} && chmod 600 {config}")
        output.ok("Created SSH config file")


def public_key(conn: Connection) -> str:
    """Read the public half of the key, ready to paste into GitHub or GitLab.

    Examples::

        public_key(conn)  # "ssh-ed25519 AAAAC3Nz... ada@example.com"
    """
    return ssh.run(conn, f'cat "{KEY_PATH}.pub"').stdout.strip()
