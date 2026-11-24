# ramani: src/msingi/ssh.py
"""Run commands on the server through the system ``ssh`` client."""

import shlex
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from .errors import MsingiError

OPTIONS = (
    "-o",
    "ConnectTimeout=10",
    "-o",
    "StrictHostKeyChecking=accept-new",
    "-o",
    "BatchMode=yes",
)

type Command = str | list[str]


@dataclass(frozen=True)
class Connection:
    """Who connects where: ``user@host:port``, with an optional private key file.

    Examples::

        Connection("203.0.113.10", "ubuntu")  # ubuntu@203.0.113.10 on port 22
        Connection("203.0.113.10", "ubuntu", 2222, Path("~/.ssh/deploy"))
    """

    host: str
    user: str
    port: int = 22
    key: Path | None = None


def as_user(conn: Connection, user: str) -> Connection:
    """Return the same connection for another user.

    Examples::

        as_user(Connection("203.0.113.10", "ubuntu"), "developer").user  # "developer"
    """
    return replace(conn, user=user)


def remote_command(conn: Connection, command: Command, sudo: bool = False) -> str:
    """Build the one string the server's shell receives.

    A string runs in ``bash -c`` (so ``$HOME``, ``~`` and pipes work); a list is quoted
    word by word. With ``sudo`` the command gets ``sudo -n`` unless we connect as root.

    Examples::

        remote_command(Connection("h", "ubuntu"), ["apt-get", "update"], sudo=True)
        # "sudo -n apt-get update"
        remote_command(Connection("h", "root"), "ls ~ | wc -l", sudo=True)
        # "bash -c 'ls ~ | wc -l'"
        remote_command(Connection("h", "dev"), ["git", "config", "user.name", "Ada L"])
        # "git config user.name 'Ada L'"
    """
    argv = ["bash", "-c", command] if isinstance(command, str) else list(command)
    if sudo and conn.user != "root":
        argv = ["sudo", "-n", *argv]
    return shlex.join(argv)


def ssh_command(conn: Connection, remote: str) -> list[str]:
    """Build the local ``ssh`` command that runs ``remote`` on the server.

    Examples::

        ssh_command(Connection("203.0.113.10", "ubuntu"), "uptime")
        # ["ssh", "-p", "22", "-o", "ConnectTimeout=10", ..., "ubuntu@203.0.113.10", "uptime"]
    """
    key = ["-i", str(conn.key), "-o", "IdentitiesOnly=yes"] if conn.key else []
    return [
        "ssh",
        "-p",
        str(conn.port),
        *key,
        *OPTIONS,
        f"{conn.user}@{conn.host}",
        remote,
    ]


def run(
    conn: Connection,
    command: Command,
    *,
    sudo: bool = False,
    input: str | None = None,
    check: bool = True,
    stream: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run ``command`` on the server.

    ``input`` goes to the command's stdin. ``stream=True`` shows the output live instead
    of capturing it. With ``check`` a non-zero exit raises MsingiError.

    Examples::

        run(conn, ["id", "developer"], check=False).returncode  # 0 if the user exists
        run(conn, ["tee", "/etc/motd"], sudo=True, input="Welcome\\n")
    """
    if shutil.which("ssh") is None:
        raise MsingiError("the OpenSSH client (ssh) was not found on this machine")

    # Bytes in, bytes out: text mode would turn "\n" into "\r\n" on Windows, which
    # corrupts files like sudoers and authorized_keys on the server.
    stdin = {"input": input.encode()} if input is not None else {"stdin": subprocess.DEVNULL}
    raw = subprocess.run(
        ssh_command(conn, remote_command(conn, command, sudo)),
        capture_output=not stream,
        **stdin,
    )
    result = subprocess.CompletedProcess(
        raw.args, raw.returncode, _text(raw.stdout), _text(raw.stderr)
    )
    if check and result.returncode != 0:
        shown = command if isinstance(command, str) else shlex.join(command)
        detail = result.stderr.strip()
        raise MsingiError(
            f"command failed on {conn.user}@{conn.host} (exit {result.returncode}): {shown}"
            + (f"\n{detail}" if detail else "")
        )
    return result


def _text(data: bytes | None) -> str:
    """Decode the server's output as UTF-8 (``""`` when nothing was captured).

    Examples::

        _text(b"ok\\n")  # "ok\\n"
        _text(None)  # ""
    """
    return (data or b"").decode("utf-8", errors="replace")


def succeeds(conn: Connection, command: Command, *, sudo: bool = False) -> bool:
    """Tell whether ``command`` exits with 0.

    Examples::

        succeeds(conn, ["id", "developer"])  # True when the user exists
    """
    return run(conn, command, sudo=sudo, check=False).returncode == 0


def command_exists(conn: Connection, name: str, *, sudo: bool = False) -> bool:
    """Tell whether a program is on the server's PATH (use ``sudo`` for sbin tools).

    Examples::

        command_exists(conn, "git")  # True
        command_exists(conn, "ufw", sudo=True)  # False on a bare image
    """
    return succeeds(conn, f"command -v {shlex.quote(name)}", sudo=sudo)


def check_connection(conn: Connection, hint: str = "") -> None:
    """Make sure we can log in, with a readable error if not.

    Examples::

        check_connection(Connection("203.0.113.10", "ubuntu"))  # None
    """
    result = run(conn, "echo ok", check=False)
    if result.returncode == 0:
        return
    reason = result.stderr.strip() or f"ssh exited with {result.returncode}"
    raise MsingiError(
        f"can't connect to {conn.user}@{conn.host}:{conn.port}: {reason}\n"
        + (f"{hint}\n" if hint else "")
        + "msingi never asks for passwords or passphrases: use a key without a passphrase "
        "(--key), or one loaded in ssh-agent (ssh-add)."
    )
