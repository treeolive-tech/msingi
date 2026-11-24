# ramani: tests/test_commands_locally.py
"""Run real commands through a stand-in ``ssh`` that executes them on this machine.

This checks the part the fake server can't: that quoting, ``$HOME``, pipes and stdin
survive the trip, and that modules really change the filesystem.
"""

import os
import shutil
import subprocess
import sys

import pytest

from msingi import ssh
from msingi.errors import MsingiError
from msingi.modules import git_ssh, repos
from msingi.ssh import Connection

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="needs a POSIX shell to stand in for ssh"
)

FAKE_SSH = """#!/bin/bash
while [ "$1" = "-p" ] || [ "$1" = "-i" ] || [ "$1" = "-o" ]; do shift 2; done
shift
exec bash -c "$*"
"""

CONN = Connection("localhost", "tester")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Put a stand-in ssh first on PATH and give it a throwaway HOME."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "ssh"
    script.write_text(FAKE_SSH)
    script.chmod(0o755)

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("HOME", str(home))
    return home


def test_strings_expand_home_and_pipes(home):
    result = ssh.run(CONN, 'echo "$HOME" | tr a-z A-Z')
    assert result.stdout.strip() == str(home).upper()


def test_input_reaches_stdin(home, tmp_path):
    target = tmp_path / "written.txt"
    ssh.run(CONN, ["tee", str(target)], input="hello\n")
    assert target.read_text() == "hello\n"


def test_failures_become_errors_and_checks_do_not(home):
    with pytest.raises(MsingiError, match="exit 3"):
        ssh.run(CONN, "exit 3")
    assert ssh.succeeds(CONN, "exit 3") is False
    assert ssh.succeeds(CONN, "true") is True


def test_command_exists(home):
    assert ssh.command_exists(CONN, "bash")
    assert not ssh.command_exists(CONN, "definitely-not-a-program")


def test_repos_module_creates_the_folder_once(home, settings):
    repos.setup(CONN, settings)
    repos.setup(CONN, settings)
    assert (home / "repos").is_dir()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_awkward_git_names_survive_quoting(home):
    name = 'O\'Brien "Q" $HOME `date`'
    git_ssh.configure_git(CONN, name, "ob@example.com")
    stored = subprocess.run(
        ["git", "config", "--global", "--get", "user.name"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert stored == name
