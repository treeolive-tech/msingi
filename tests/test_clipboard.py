# ramani: tests/test_clipboard.py
"""Copying the Git public key to the clipboard."""

import sys
import types
from dataclasses import replace

import pytest

from msingi import cli, clipboard, runner
from msingi.errors import MsingiError
from msingi.profiles import PROFILES
from msingi.settings import validate

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEx ada@example.com"
UFW_READY = "Status: active\nOpenSSH    ALLOW    Anywhere\nNginx Full    ALLOW    Anywhere\n"


class FakePyperclip(types.ModuleType):
    """Stands in for pyperclip: remembers what was copied, or raises like a missing clipboard."""

    class PyperclipException(RuntimeError):
        """Same name as pyperclip's own error."""

    def __init__(self, broken: bool = False) -> None:
        super().__init__("pyperclip")
        self.broken = broken
        self.copied: list[str] = []

    def copy(self, text: str) -> None:
        """Record the text, or fail when ``broken``."""
        if self.broken:
            raise self.PyperclipException("could not find a copy/paste mechanism")
        self.copied.append(text)


@pytest.fixture
def pyperclip(monkeypatch) -> FakePyperclip:
    """A working fake clipboard installed in place of pyperclip."""
    fake = FakePyperclip()
    monkeypatch.setitem(sys.modules, "pyperclip", fake)
    return fake


@pytest.fixture
def git_run(server, settings):
    """Settings for a git-ssh run on a server that can hand back a public key."""
    server.when("id_ed25519.pub", stdout=KEY + "\n")
    server.when("ufw status", stdout=UFW_READY)
    return replace(settings, modules=("git-ssh",), profile="custom", copy_key=True)


def test_copy_puts_the_text_on_the_clipboard(pyperclip):
    clipboard.copy(KEY)
    assert pyperclip.copied == [KEY]


def test_copy_explains_a_missing_clipboard(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyperclip", FakePyperclip(broken=True))
    with pytest.raises(MsingiError, match="no clipboard available: could not find"):
        clipboard.copy(KEY)


def test_copy_explains_a_missing_pyperclip(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyperclip", None)  # makes `import pyperclip` fail
    with pytest.raises(MsingiError, match="pyperclip is not installed"):
        clipboard.copy(KEY)


def test_run_copies_the_new_key_when_asked(git_run, pyperclip, capsys):
    runner.provision(git_run)
    assert pyperclip.copied == [KEY]
    out = capsys.readouterr().out
    assert KEY in out
    assert "Public key copied to the clipboard" in out


def test_run_does_not_copy_unless_asked(git_run, pyperclip, capsys):
    runner.provision(replace(git_run, copy_key=False))
    assert pyperclip.copied == []
    assert "copied to the clipboard" not in capsys.readouterr().out


def test_a_broken_clipboard_only_warns_and_the_key_is_still_printed(git_run, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "pyperclip", FakePyperclip(broken=True))
    runner.provision(git_run)
    out = capsys.readouterr().out
    assert KEY in out
    assert "Could not copy the key: no clipboard available" in out
    assert "Setup completed successfully!" in out


def test_dry_run_copies_nothing(git_run, pyperclip):
    runner.provision(replace(git_run, dry_run=True))
    assert pyperclip.copied == []


def test_copy_needs_the_git_ssh_module(settings):
    with pytest.raises(MsingiError, match="--copy needs the git-ssh module"):
        validate(
            replace(settings, modules=("repos",), copy_key=True), needs_sudo=False, needs_git=False
        )


def test_copy_flag_reaches_the_settings(monkeypatch):
    seen = []
    monkeypatch.setattr(runner, "provision", seen.append)
    cli.main(["203.0.113.10", "dev", "-s", "ubuntu", "--copy", "--git-name", "Ada", "--git-email", "ada@example.com"])
    assert seen[0].copy_key
    assert seen[0].modules == PROFILES["full"][1]
    cli.main(["203.0.113.10", "dev", "-s", "ubuntu"])
    assert not seen[1].copy_key
