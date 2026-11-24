# ramani: src/msingi/modules/openssh_ufw.py
"""Allow SSH through the UFW firewall, then switch the firewall on."""

from .. import output, ssh, system
from ..errors import MsingiError
from ..settings import Settings
from ..ssh import Connection

NAME = "openssh-ufw"
TITLE = "OpenSSH and UFW"
SYSTEM = True


def setup(conn: Connection, settings: Settings) -> None:
    """Install UFW, allow SSH, and enable UFW only once the SSH rule is confirmed.

    Examples::

        setup(conn, settings)  # ✅ UFW enabled successfully
    """
    if not system.ensure_ufw(conn):
        return
    if not allow_ssh(conn, settings):
        return

    if not system.ufw_has_rule(conn, "OpenSSH"):
        raise MsingiError(
            "OpenSSH rule not confirmed in UFW, so UFW was not enabled (this prevents a lockout)"
        )
    enable_ufw(conn)


def allow_ssh(conn: Connection, settings: Settings) -> bool:
    """Allow the OpenSSH profile, plus the custom port when SSH doesn't use 22.

    Examples::

        allow_ssh(conn, settings)  # True
    """
    if system.ufw_has_rule(conn, "OpenSSH"):
        output.ok("OpenSSH rule already exists in UFW")
    else:
        output.step("Adding OpenSSH rule to UFW...")
        if not system.ufw_allow(conn, "OpenSSH"):
            return False

    if settings.port != 22:
        port_rule = f"{settings.port}/tcp"
        if not system.ufw_has_rule(conn, port_rule):
            output.step(f"Adding SSH port rule {port_rule} to UFW...")
            return system.ufw_allow(conn, port_rule)
    return True


def enable_ufw(conn: Connection) -> None:
    """Switch UFW on unless it already is.

    Examples::

        enable_ufw(conn)  # ✅ UFW already enabled
    """
    if system.ufw_is_active(conn):
        output.ok("UFW already enabled")
        return

    output.step("Enabling UFW firewall...")
    if ssh.succeeds(conn, ["ufw", "--force", "enable"], sudo=True):
        output.ok("UFW enabled successfully")
    else:
        output.warn("Failed to enable ufw")
