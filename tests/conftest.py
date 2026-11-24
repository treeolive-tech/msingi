# ramani: tests/conftest.py
"""Shared test tools: a fake server that records commands instead of running ssh."""

import shlex
import subprocess
from dataclasses import dataclass

import pytest

from msingi import ssh
from msingi.errors import MsingiError
from msingi.settings import Settings
from msingi.ssh import Connection


@dataclass
class Call:
    """One command sent to the fake server."""

    user: str
    text: str
    sudo: bool
    input: str | None


class FakeServer:
    """Stands in for ``ssh.run``: records every call and answers from scripted replies.

    Examples::

        server.when("command -v nginx", returncode=1)  # nginx is missing
        server.when("ufw status", stdout=("first answer", "then this one"))
    """

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.replies: list[tuple[str, str | None, list[str], int]] = []

    def when(
        self,
        fragment: str,
        *,
        user: str | None = None,
        stdout: str | tuple[str, ...] = "",
        returncode: int = 0,
    ) -> None:
        """Answer commands containing ``fragment``; the first matching reply wins."""
        outputs = [stdout] if isinstance(stdout, str) else list(stdout)
        self.replies.append((fragment, user, outputs, returncode))

    def __call__(
        self, conn, command, *, sudo=False, input=None, check=True, stream=False
    ):
        """Record the call and return the scripted answer (success with no output by default)."""
        text = command if isinstance(command, str) else shlex.join(command)
        self.calls.append(Call(conn.user, text, sudo, input))

        stdout, returncode = "", 0
        for fragment, user, outputs, code in self.replies:
            if fragment in text and user in (None, conn.user):
                stdout = outputs.pop(0) if len(outputs) > 1 else outputs[0]
                returncode = code
                break

        if check and returncode != 0:
            raise MsingiError(f"command failed: {text}")
        return subprocess.CompletedProcess(text, returncode, stdout, "")

    def ran(self, fragment: str) -> bool:
        """Tell whether any command contained ``fragment``."""
        return any(fragment in call.text for call in self.calls)

    def find(self, fragment: str) -> Call:
        """Return the first call containing ``fragment``."""
        return next(call for call in self.calls if fragment in call.text)


@pytest.fixture
def server(monkeypatch) -> FakeServer:
    """A fake server wired in place of ``ssh.run``."""
    fake = FakeServer()
    monkeypatch.setattr(ssh, "run", fake)
    return fake


@pytest.fixture
def admin() -> Connection:
    """The connection used for system work."""
    return Connection("203.0.113.10", "ubuntu")


@pytest.fixture
def user_conn() -> Connection:
    """The connection used for user work."""
    return Connection("203.0.113.10", "developer")


@pytest.fixture
def settings() -> Settings:
    """A complete set of settings; tests change what they care about with ``replace``."""
    return Settings(
        host="203.0.113.10",
        target_user="developer",
        sudo_user="ubuntu",
        git_user_name="Ada Lovelace",
        git_user_email="ada@example.com",
    )
