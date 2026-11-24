# ramani: tests/test_cli.py
"""The command line: arguments in, settings out."""

import pytest

from msingi import cli, runner
from msingi.errors import MsingiError
from msingi.profiles import PROFILES

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEx ada@laptop"


@pytest.fixture
def seen(monkeypatch):
    """Capture the settings the CLI would provision with."""
    captured = []
    monkeypatch.setattr(runner, "provision", captured.append)
    return captured


def test_defaults_to_the_full_profile(seen):
    assert cli.main(["203.0.113.10", "developer", "-s", "ubuntu"]) == 0
    settings = seen[0]
    assert settings.profile == "full"
    assert settings.modules == PROFILES["full"][1]
    assert (settings.host, settings.target_user, settings.sudo_user) == (
        "203.0.113.10",
        "developer",
        "ubuntu",
    )
    assert settings.port == 22
    assert not settings.dry_run


def test_modules_flag_makes_a_custom_profile(seen):
    cli.main(["203.0.113.10", "dev", "-m", "nginx, nvm"])
    assert seen[0].profile == "custom"
    assert seen[0].modules == ("nginx", "nvm")


def test_profile_flag(seen):
    cli.main(["203.0.113.10", "dev", "-P", "user"])
    assert seen[0].profile == "user"
    assert seen[0].modules == PROFILES["user"][1]


@pytest.mark.parametrize(
    "extra",
    [["-P", "user", "-m", "nginx"], ["-P", "custom"], ["-m", "nope"], ["-P", "bogus"]],
)
def test_bad_module_choices_exit_with_a_usage_error(seen, extra, capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["203.0.113.10", "dev", *extra])
    assert exit_.value.code == 2
    assert seen == []


def test_the_other_flags_reach_the_settings(seen):
    cli.main(
        [
            "203.0.113.10", "dev", "-p", "2222", "--make-sudo", "-n",
            "--git-name", "Ada Lovelace", "--git-email", "ada@example.com",
            "--nvm-version", "v0.39.7", "--public-key", KEY,
        ]
    )  # fmt: skip
    settings = seen[0]
    assert settings.port == 2222
    assert settings.make_user_sudo
    assert settings.dry_run
    assert (settings.git_user_name, settings.git_user_email) == (
        "Ada Lovelace",
        "ada@example.com",
    )
    assert settings.nvm_version == "v0.39.7"
    assert settings.ssh_public_key == KEY


def test_public_key_can_be_a_file(seen, tmp_path):
    file = tmp_path / "id.pub"
    file.write_text(KEY + "\n")
    cli.main(["203.0.113.10", "dev", "--public-key", str(file)])
    assert seen[0].ssh_public_key == KEY


def test_missing_public_key_file_is_a_usage_error(seen, tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["203.0.113.10", "dev", "--public-key", str(tmp_path / "nope.pub")])


def test_environment_variables_fill_in_defaults(seen, monkeypatch, tmp_path):
    key = tmp_path / "deploy"
    key.write_text("private")
    monkeypatch.setenv("MSINGI_SUDO_USER", "admin")
    monkeypatch.setenv("MSINGI_SSH_KEY", str(key))
    monkeypatch.setenv("MSINGI_NVM_VERSION", "v0.38.0")
    cli.main(["203.0.113.10", "dev"])
    settings = seen[0]
    assert settings.sudo_user == "admin"
    assert settings.key == key
    assert settings.nvm_version == "v0.38.0"


def test_flags_beat_environment_variables(seen, monkeypatch):
    monkeypatch.setenv("MSINGI_SUDO_USER", "admin")
    cli.main(["203.0.113.10", "dev", "-s", "ubuntu"])
    assert seen[0].sudo_user == "ubuntu"


def test_a_failed_run_exits_with_one_and_prints_why(monkeypatch, capsys):
    def boom(settings):
        raise MsingiError("something broke")

    monkeypatch.setattr(runner, "provision", boom)
    assert cli.main(["203.0.113.10", "dev"]) == 1
    assert "msingi: something broke" in capsys.readouterr().err


def test_help_lists_profiles_and_modules(capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["--help"])
    assert exit_.value.code == 0
    out = capsys.readouterr().out
    for name in (
        "full",
        "system",
        "user",
        "custom",
        "openssh-ufw",
        "git-ssh",
        "certbot",
    ):
        assert name in out


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["--version"])
    assert exit_.value.code == 0
    assert capsys.readouterr().out.startswith("msingi ")
