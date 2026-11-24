# ramani: src/msingi/account.py
"""Create the user to set up, give it sudo if asked, and let it log in with a key."""

from . import output, ssh
from .settings import Settings
from .ssh import Connection


def ensure_user(conn: Connection, settings: Settings) -> None:
    """Create the target user if missing, then apply the sudo and public key options.

    Runs as the admin connection. On a dry run it only says what it would do.

    Examples::

        ensure_user(admin, settings)  # ✅ User developer already exists
    """
    user = settings.target_user

    if ssh.succeeds(conn, ["id", user]):
        output.ok(f"User {user} already exists")
    elif settings.dry_run:
        output.dry(f"create user: {user}")
    else:
        output.step(f"🔧 Creating user: {user}")
        ssh.run(conn, ["useradd", "-m", "-s", "/bin/bash", user], sudo=True)
        output.ok(f"User {user} created successfully")

    if settings.make_user_sudo:
        grant_sudo(conn, settings)
    if settings.ssh_public_key:
        add_public_key(conn, settings)


def grant_sudo(conn: Connection, settings: Settings) -> None:
    """Add the user to the sudo group with passwordless sudo.

    Examples::

        grant_sudo(admin, settings)  # writes /etc/sudoers.d/developer
    """
    user = settings.target_user
    if settings.dry_run:
        output.dry(f"grant sudo privileges to: {user}")
        return

    output.step(f"🔧 Ensuring {user} is a sudoer")
    ssh.run(conn, ["usermod", "-aG", "sudo", user], sudo=True)
    sudoers = f"/etc/sudoers.d/{user}"
    ssh.run(conn, ["tee", sudoers], sudo=True, input=f"{user} ALL=(ALL) NOPASSWD:ALL\n")
    ssh.run(conn, ["chmod", "440", sudoers], sudo=True)
    output.ok(f"{user} has sudo privileges")


def home_of(conn: Connection, user: str) -> str:
    """Look up a user's home directory.

    Examples::

        home_of(admin, "developer")  # "/home/developer"
    """
    entry = ssh.run(conn, ["getent", "passwd", user]).stdout.strip()
    return entry.split(":")[5]


def add_public_key(conn: Connection, settings: Settings) -> None:
    """Add the public key to the user's ``authorized_keys`` unless it is already there.

    Examples::

        add_public_key(admin, settings)  # ✅ Public key added
    """
    user, key = settings.target_user, settings.ssh_public_key.strip()
    if settings.dry_run:
        output.dry(f"add SSH public key for {user}")
        return

    output.step(f"🔑 Adding SSH public key for {user}")
    ssh_dir = f"{home_of(conn, user)}/.ssh"
    authorized = f"{ssh_dir}/authorized_keys"

    ssh.run(conn, ["mkdir", "-p", ssh_dir], sudo=True)
    current = ssh.run(conn, ["cat", authorized], sudo=True, check=False).stdout
    if key in (line.strip() for line in current.splitlines()):
        output.ok("Public key already exists")
    else:
        separator = "" if not current or current.endswith("\n") else "\n"
        ssh.run(conn, ["tee", "-a", authorized], sudo=True, input=f"{separator}{key}\n")
        output.ok("Public key added")

    ssh.run(conn, ["chmod", "700", ssh_dir], sudo=True)
    ssh.run(conn, ["chmod", "600", authorized], sudo=True)
    ssh.run(conn, ["chown", "-R", f"{user}:{user}", ssh_dir], sudo=True)
