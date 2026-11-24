# ramani: src/msingi/system.py
"""Server chores the system modules share: apt, services and the UFW firewall."""

import re

from . import output, ssh
from .errors import MsingiError
from .ssh import Connection


def apt_update(conn: Connection) -> None:
    """Refresh the package lists.

    Examples::

        apt_update(conn)  # runs: sudo apt-get update -y
    """
    apt(conn, "update", "-y")


def apt_install(conn: Connection, *packages: str) -> None:
    """Install packages without any prompts.

    Examples::

        apt_install(conn, "nginx")  # runs: sudo apt-get install -y nginx
    """
    apt(conn, "install", "-y", *packages)


def apt(conn: Connection, *args: str) -> None:
    """Run ``apt-get`` as root, non-interactively, with its output shown live."""
    command = ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", *args]
    ssh.run(conn, command, sudo=True, stream=True)


def enable_and_start(conn: Connection, service: str) -> None:
    """Enable a systemd service at boot and start it, skipping what is already done.

    Examples::

        enable_and_start(conn, "nginx")  # nothing happens if it is enabled and running
    """
    if not ssh.succeeds(
        conn, ["systemctl", "is-enabled", "--quiet", service], sudo=True
    ):
        ssh.run(conn, ["systemctl", "enable", service], sudo=True)
    if not ssh.succeeds(
        conn, ["systemctl", "is-active", "--quiet", service], sudo=True
    ):
        ssh.run(conn, ["systemctl", "start", service], sudo=True)


def ensure_ufw(conn: Connection) -> bool:
    """Make sure UFW is installed; False, with a warning, if it can't be.

    Examples::

        ensure_ufw(conn)  # True
    """
    if ssh.command_exists(conn, "ufw", sudo=True):
        return True
    try:
        apt_install(conn, "ufw")
    except MsingiError:
        output.warn("Failed to install ufw")
        return False
    return True


def ufw_has_rule(conn: Connection, rule: str) -> bool:
    """Tell whether UFW allows ``rule``, whether UFW is switched on yet or not.

    Examples::

        ufw_has_rule(conn, "OpenSSH")  # True after `ufw allow OpenSSH`
    """
    status = ssh.run(conn, ["ufw", "status"], sudo=True, check=False).stdout
    if any(rule in line and "ALLOW" in line for line in status.splitlines()):
        return True
    added = ssh.run(conn, ["ufw", "show", "added"], sudo=True, check=False).stdout
    return re.search(rf"ufw allow.*{re.escape(rule)}", added) is not None


def ufw_is_active(conn: Connection) -> bool:
    """Tell whether the firewall is switched on.

    Examples::

        ufw_is_active(conn)  # False on a fresh server
    """
    status = ssh.run(conn, ["ufw", "status"], sudo=True, check=False).stdout
    return "Status: active" in status


def ufw_allow(conn: Connection, rule: str) -> bool:
    """Allow ``rule`` in UFW; False, with a warning, if UFW refuses.

    Examples::

        ufw_allow(conn, "Nginx Full")  # True
        ufw_allow(conn, "2222/tcp")  # True
    """
    if ssh.succeeds(conn, ["ufw", "allow", rule], sudo=True):
        return True
    output.warn(f"Failed to allow {rule} in ufw")
    return False
