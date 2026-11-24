# ramani: src/msingi/profiles.py
"""The ready-made module sets, and how a profile or a custom list picks modules."""

from collections.abc import Sequence

from .errors import MsingiError

SYSTEM_MODULES = ("openssh-ufw", "packages", "nginx", "certbot", "postgres")
USER_MODULES = ("uv", "nvm", "repos", "git-ssh")

# profile -> (label shown in the run, module names)
PROFILES: dict[str, tuple[str, tuple[str, ...]]] = {
    "full": ("Full Development Server", SYSTEM_MODULES + USER_MODULES),
    "system": ("System Services Only", SYSTEM_MODULES),
    "user": ("User Tools Only", USER_MODULES),
    "custom": ("Custom (chosen modules)", ()),
}


def choose(
    profile: str | None, names: Sequence[str] = ()
) -> tuple[str, tuple[str, ...]]:
    """Resolve ``--profile`` and ``--modules`` into (profile, module names).

    Naming modules means a custom profile; naming none means the profile's own set
    (``full`` when nothing was asked).

    Examples::

        choose(None)  # ("full", ("openssh-ufw", ..., "git-ssh"))
        choose("user")  # ("user", ("uv", "nvm", "repos", "git-ssh"))
        choose(None, ["nginx", "nvm"])  # ("custom", ("nginx", "nvm"))
        choose("custom")  # MsingiError: --profile custom needs --modules
    """
    known = SYSTEM_MODULES + USER_MODULES
    if unknown := [name for name in names if name not in known]:
        raise MsingiError(
            f"unknown module(s): {', '.join(unknown)} (choose from {', '.join(known)})"
        )
    if names and profile not in (None, "custom"):
        raise MsingiError(f"--modules can't be combined with --profile {profile}")
    if names:
        return "custom", tuple(dict.fromkeys(names))
    if profile == "custom":
        raise MsingiError("--profile custom needs --modules")
    profile = profile or "full"
    return profile, PROFILES[profile][1]
