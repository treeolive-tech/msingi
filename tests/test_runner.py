# ramani: tests/test_runner.py
"""A whole run on a fake server."""

from dataclasses import replace

import pytest

from msingi import runner
from msingi.errors import MsingiError
from msingi.profiles import PROFILES

PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEx ada@example.com"


UFW_READY = (
    "Status: active\nOpenSSH    ALLOW    Anywhere\nNginx Full    ALLOW    Anywhere\n"
)


@pytest.fixture
def full(settings, server):
    """Settings for the full profile, on a server whose firewall already allows SSH."""
    server.when("ufw status", stdout=UFW_READY)
    return replace(settings, modules=PROFILES["full"][1])


def test_dry_run_only_looks(server, full, capsys):
    server.when("id developer", returncode=1)
    runner.provision(replace(full, dry_run=True, make_user_sudo=True))

    assert {call.text for call in server.calls} == {"echo ok", "id developer"}
    out = capsys.readouterr().out
    assert "DRY RUN MODE ENABLED" in out
    for line in (
        "[DRY RUN] Would create user: developer",
        "[DRY RUN] Would run apt-get update",
        "[DRY RUN] Would set up OpenSSH and UFW",
        "[DRY RUN] Would set up necessary packages",
        "[DRY RUN] Would set up Nginx",
        "[DRY RUN] Would set up uv",
        "[DRY RUN] Would set up Git and SSH",
    ):
        assert line in out
    assert "Dry run completed" in out
    assert "SSH public key" not in out


def test_system_modules_run_as_the_sudo_user_and_user_modules_as_the_target(
    server, full, capsys
):
    server.when("id_ed25519.pub", stdout=PUBLIC_KEY + "\n")
    runner.provision(full)

    packages = next(
        i for i, c in enumerate(server.calls) if "apt-get install -y git" in c.text
    )
    git = next(
        i
        for i, c in enumerate(server.calls)
        if "git config --global user.name" in c.text
    )
    assert server.calls[packages].user == "ubuntu"
    assert server.calls[git].user == "developer"
    assert packages < git

    out = capsys.readouterr().out
    assert "Setup completed successfully!" in out
    assert PUBLIC_KEY in out


def test_modules_run_in_registry_order_whatever_the_selection_order(
    server, settings, capsys
):
    runner.provision(replace(settings, modules=("nvm", "nginx"), profile="custom"))
    out = capsys.readouterr().out
    assert out.index("Setting up Nginx") < out.index("Setting up nvm")


def test_package_lists_are_updated_once_before_system_modules(server, full):
    runner.provision(replace(full, modules=("packages", "nginx")))
    updates = [i for i, c in enumerate(server.calls) if "apt-get update" in c.text]
    installs = [i for i, c in enumerate(server.calls) if "apt-get install" in c.text]
    assert len(updates) == 1
    assert updates[0] < min(installs)


def test_user_only_runs_never_update_packages(server, settings):
    runner.provision(replace(settings, modules=("repos",), profile="custom"))
    assert not server.ran("apt-get")


def test_missing_sudo_user_stops_before_touching_the_server(server, full):
    with pytest.raises(MsingiError, match="sudo user is required"):
        runner.provision(replace(full, sudo_user=""))
    assert server.calls == []


def test_user_modules_connect_as_the_target_when_there_is_no_sudo_user(
    server, settings
):
    runner.provision(
        replace(settings, sudo_user="", modules=("repos",), profile="custom")
    )
    assert {call.user for call in server.calls} == {"developer"}


def test_target_user_that_cannot_log_in_gets_a_hint(server, settings):
    server.when("echo ok", user="developer", returncode=255)
    with pytest.raises(MsingiError, match="--public-key"):
        runner.provision(replace(settings, modules=("repos",), profile="custom"))
    assert not server.ran("mkdir")


def test_a_failing_module_stops_the_run(server, full):
    server.when("apt-get install -y git", returncode=100)
    with pytest.raises(MsingiError):
        runner.provision(full)
    assert not server.ran("git config")
