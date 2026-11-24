# ramani: tests/test_settings_profiles.py
"""Input checks, profile choice and the module registry."""

from dataclasses import replace

import pytest

from msingi import modules
from msingi.errors import MsingiError
from msingi.profiles import SYSTEM_MODULES, USER_MODULES, choose
from msingi.settings import is_public_key, validate

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEx ada@laptop"


def check(settings, **flags):
    """Validate with modules chosen, defaulting to a user module only."""
    settings = replace(settings, modules=settings.modules or ("repos",))
    validate(settings, needs_sudo=flags.get("needs_sudo", False), needs_git=flags.get("needs_git", False))


def test_valid_settings_pass(settings):
    check(settings, needs_sudo=True, needs_git=True)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"modules": ()}, "no modules selected"),
        ({"host": "bad host;rm"}, "invalid host"),
        ({"port": 0}, "invalid port"),
        ({"port": 70000}, "invalid port"),
        ({"target_user": "Dev Op"}, "invalid user name"),
        ({"target_user": "-rf"}, "invalid user name"),
        ({"sudo_user": "root;ls"}, "invalid sudo user name"),
        ({"nvm_version": "latest; rm -rf /"}, "invalid nvm version"),
        ({"ssh_public_key": "not a key"}, "public key must be one line"),
        ({"ssh_public_key": KEY + "\nssh-rsa other"}, "public key must be one line"),
    ],
)
def test_bad_input_is_rejected(settings, change, message):
    bad = replace(settings, **{"modules": ("repos",), **change})
    with pytest.raises(MsingiError, match=message):
        validate(bad, needs_sudo=False, needs_git=False)


def test_sudo_user_is_required_for_system_modules(settings):
    with pytest.raises(MsingiError, match="sudo user is required"):
        check(replace(settings, sudo_user=""), needs_sudo=True)


def test_git_name_and_email_are_required_for_git_ssh(settings):
    with pytest.raises(MsingiError, match="--git-name and --git-email"):
        check(replace(settings, git_user_name=""), needs_git=True)


def test_git_email_must_look_like_an_email(settings):
    with pytest.raises(MsingiError, match="invalid email"):
        check(replace(settings, git_user_email="ada@"), needs_git=True)


def test_missing_key_file_is_reported(settings, tmp_path):
    with pytest.raises(MsingiError, match="key file not found"):
        check(replace(settings, key=tmp_path / "nope"))


def test_public_key_shapes():
    assert is_public_key(KEY)
    assert is_public_key(KEY + "\n")
    assert not is_public_key("")
    assert not is_public_key("ssh-rsa a\nssh-rsa b")


def test_default_profile_is_full():
    profile, names = choose(None)
    assert profile == "full"
    assert names == SYSTEM_MODULES + USER_MODULES


def test_named_profiles():
    assert choose("system") == ("system", SYSTEM_MODULES)
    assert choose("user") == ("user", USER_MODULES)


def test_naming_modules_means_custom():
    assert choose(None, ["nvm", "nginx", "nvm"]) == ("custom", ("nvm", "nginx"))
    assert choose("custom", ["nginx"]) == ("custom", ("nginx",))


def test_custom_needs_modules():
    with pytest.raises(MsingiError, match="needs --modules"):
        choose("custom")


def test_modules_conflict_with_other_profiles():
    with pytest.raises(MsingiError, match="can't be combined"):
        choose("full", ["nginx"])


def test_unknown_module_lists_the_choices():
    with pytest.raises(MsingiError, match=r"unknown module\(s\): nope .*openssh-ufw"):
        choose(None, ["nope"])


def test_registry_matches_the_profile_names_and_order():
    assert modules.NAMES == SYSTEM_MODULES + USER_MODULES


def test_system_flag_matches_the_profile_groups():
    for module in modules.MODULES:
        assert module.SYSTEM == (module.NAME in SYSTEM_MODULES)


def test_by_name_returns_running_order():
    assert [m.NAME for m in modules.by_name(["nvm", "nginx"])] == ["nginx", "nvm"]


def test_by_name_rejects_unknown_names():
    with pytest.raises(MsingiError, match="unknown module: nope"):
        modules.by_name(["nope"])
