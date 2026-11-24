# ramani: tests/test_ssh.py
"""Building ssh commands and running them."""

import subprocess
from pathlib import Path

import pytest

from msingi import ssh
from msingi.errors import MsingiError
from msingi.ssh import Connection, remote_command, ssh_command

UBUNTU = Connection("203.0.113.10", "ubuntu")
ROOT = Connection("203.0.113.10", "root")


def test_lists_are_quoted_word_by_word():
    command = ["git", "config", "user.name", "Ada L"]
    assert remote_command(UBUNTU, command) == "git config user.name 'Ada L'"


def test_strings_run_in_bash_so_shell_syntax_works():
    assert remote_command(UBUNTU, "echo $HOME | wc -c") == "bash -c 'echo $HOME | wc -c'"


def test_sudo_is_added_unless_root():
    assert remote_command(UBUNTU, ["apt-get", "update"], sudo=True) == "sudo -n apt-get update"
    assert remote_command(ROOT, ["apt-get", "update"], sudo=True) == "apt-get update"
    assert remote_command(UBUNTU, "ls | wc -l", sudo=True) == "sudo -n bash -c 'ls | wc -l'"


def test_ssh_command_targets_user_host_and_port():
    command = ssh_command(Connection("example.com", "dev", 2222), "uptime")
    assert command[:3] == ["ssh", "-p", "2222"]
    assert command[-2:] == ["dev@example.com", "uptime"]
    assert "BatchMode=yes" in command
    assert "-i" not in command


def test_ssh_command_uses_the_key_only():
    command = ssh_command(Connection("h", "dev", key=Path("/keys/deploy")), "uptime")
    assert command[command.index("-i") + 1] == "/keys/deploy"
    assert "IdentitiesOnly=yes" in command


def fake_subprocess(monkeypatch, returncode=0, stdout="", stderr=""):
    """Replace subprocess.run; returns the list that records (args, kwargs) pairs."""
    seen = []

    def fake(args, **kwargs):
        seen.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode, stdout.encode(), stderr.encode())

    monkeypatch.setattr(ssh.shutil, "which", lambda name: "/usr/bin/ssh")
    monkeypatch.setattr(ssh.subprocess, "run", fake)
    return seen


def test_run_without_input_closes_stdin(monkeypatch):
    seen = fake_subprocess(monkeypatch, stdout="hi")
    result = ssh.run(UBUNTU, ["echo", "hi"])
    kwargs = seen[0][1]
    assert result.stdout == "hi"
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert "input" not in kwargs


def test_run_sends_input_to_stdin_as_bytes_with_unix_line_endings(monkeypatch):
    seen = fake_subprocess(monkeypatch)
    ssh.run(UBUNTU, ["tee", "/etc/sudoers.d/dev"], input="dev ALL=(ALL) NOPASSWD:ALL\n")
    sent = seen[0][1]["input"]
    assert sent == b"dev ALL=(ALL) NOPASSWD:ALL\n"
    assert b"\r" not in sent
    assert "text" not in seen[0][1]


def test_output_is_decoded_as_utf8_even_if_invalid(monkeypatch):
    fake_subprocess(monkeypatch, stdout="Zawadi ✓")
    assert ssh.run(UBUNTU, "true").stdout == "Zawadi ✓"
    assert ssh._text(b"bad \xff byte") == "bad � byte"
    assert ssh._text(None) == ""


def test_run_streams_when_asked(monkeypatch):
    seen = fake_subprocess(monkeypatch)
    ssh.run(UBUNTU, "true", stream=True)
    assert seen[0][1]["capture_output"] is False


def test_failed_command_raises_with_the_error_text(monkeypatch):
    fake_subprocess(monkeypatch, returncode=3, stderr="permission denied\n")
    with pytest.raises(MsingiError, match="exit 3.*\npermission denied"):
        ssh.run(UBUNTU, ["false"])


def test_check_false_returns_the_failure(monkeypatch):
    fake_subprocess(monkeypatch, returncode=1)
    assert ssh.run(UBUNTU, ["false"], check=False).returncode == 1
    assert ssh.succeeds(UBUNTU, ["false"]) is False


def test_missing_ssh_client_is_explained(monkeypatch):
    monkeypatch.setattr(ssh.shutil, "which", lambda name: None)
    with pytest.raises(MsingiError, match="OpenSSH client"):
        ssh.run(UBUNTU, "true")


def test_connection_error_has_reason_and_hint(monkeypatch):
    fake_subprocess(monkeypatch, returncode=255, stderr="Permission denied (publickey).\n")
    with pytest.raises(MsingiError) as err:
        ssh.check_connection(UBUNTU, hint="Try --key.")
    message = str(err.value)
    assert "ubuntu@203.0.113.10:22" in message
    assert "Permission denied (publickey)." in message
    assert "Try --key." in message
    assert "never asks for passwords or passphrases" in message
