# ramani: src/msingi/settings.py
"""What a run needs to know, and the checks that keep bad input off the server."""

import re
from dataclasses import dataclass
from pathlib import Path

from .errors import MsingiError

DEFAULT_NVM_VERSION = "v0.40.4"
KEY_PREFIXES = ("ssh-", "ecdsa-", "sk-")

USER_RE = re.compile(r"[a-z_][a-z0-9_-]{0,31}")
HOST_RE = re.compile(r"[A-Za-z0-9._:-]+")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")


@dataclass(frozen=True)
class Settings:
    """Everything one run is told: where to go, who to set up, and which modules.

    ``sudo_user`` is the existing account used for system work. ``modules`` holds module
    names (see ``profiles.py``); ``profile`` is only used to label the run.

    Examples::

        Settings("203.0.113.10", "developer", sudo_user="ubuntu", modules=("nginx",))
    """

    host: str
    target_user: str
    port: int = 22
    key: Path | None = None
    sudo_user: str = ""
    make_user_sudo: bool = False
    ssh_public_key: str = ""
    profile: str = "full"
    modules: tuple[str, ...] = ()
    git_user_name: str = ""
    git_user_email: str = ""
    nvm_version: str = DEFAULT_NVM_VERSION
    copy_key: bool = False
    dry_run: bool = False


def is_public_key(text: str) -> bool:
    """Tell whether ``text`` is a single-line SSH public key.

    Examples::

        is_public_key("ssh-ed25519 AAAAC3Nz... ada@laptop")  # True
        is_public_key("hello")  # False
    """
    lines = text.strip().splitlines()
    return len(lines) == 1 and lines[0].startswith(KEY_PREFIXES)


def validate(settings: Settings, *, needs_sudo: bool, needs_git: bool) -> None:
    """Raise MsingiError for the first problem found in ``settings``.

    ``needs_sudo`` is True when a system module will run, ``needs_git`` when git-ssh will.

    Examples::

        validate(Settings("203.0.113.10", "developer"), needs_sudo=True, needs_git=False)
        # MsingiError: a sudo user is required for system modules (--sudo-user)
    """
    if not settings.modules:
        raise MsingiError("no modules selected")
    if not HOST_RE.fullmatch(settings.host):
        raise MsingiError(f"invalid host: {settings.host!r}")
    if not 1 <= settings.port <= 65535:
        raise MsingiError(f"invalid port: {settings.port}")
    for label, name in (("user", settings.target_user), ("sudo user", settings.sudo_user)):
        if name and not USER_RE.fullmatch(name):
            raise MsingiError(f"invalid {label} name: {name!r}")
    if not settings.target_user:
        raise MsingiError("a user to set up is required")
    if not VERSION_RE.fullmatch(settings.nvm_version):
        raise MsingiError(f"invalid nvm version {settings.nvm_version!r} (like v0.40.4)")
    if settings.key and not settings.key.is_file():
        raise MsingiError(f"SSH key file not found: {settings.key}")
    if settings.ssh_public_key and not is_public_key(settings.ssh_public_key):
        raise MsingiError("the public key must be one line like 'ssh-ed25519 AAAA... comment'")
    if needs_sudo and not settings.sudo_user:
        raise MsingiError("a sudo user is required for system modules (--sudo-user)")
    if settings.copy_key and not needs_git:
        raise MsingiError("--copy needs the git-ssh module (it copies the new Git public key)")
    if needs_git:
        if not (settings.git_user_name and settings.git_user_email):
            raise MsingiError("--git-name and --git-email are required for the git-ssh module")
        if not EMAIL_RE.fullmatch(settings.git_user_email):
            raise MsingiError(f"invalid email format: {settings.git_user_email}")
