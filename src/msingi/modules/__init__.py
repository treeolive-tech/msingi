# ramani: src/msingi/modules/__init__.py
"""The setup modules, in the order they run.

Each module has ``NAME`` (used on the command line), ``TITLE`` (shown in the run),
``SYSTEM`` (True when it needs sudo) and ``setup(conn, settings)``.
"""

from collections.abc import Iterable
from types import ModuleType

from ..errors import MsingiError
from . import certbot, git_ssh, nginx, nvm, openssh_ufw, packages, postgres, repos, uv

MODULES: tuple[ModuleType, ...] = (
    openssh_ufw,
    packages,
    nginx,
    certbot,
    postgres,
    uv,
    nvm,
    repos,
    git_ssh,
)
NAMES = tuple(module.NAME for module in MODULES)


def by_name(names: Iterable[str]) -> list[ModuleType]:
    """Pick modules by name, always in running order.

    Examples::

        [m.NAME for m in by_name(["nvm", "nginx"])]  # ["nginx", "nvm"]
        by_name(["nope"])  # MsingiError: unknown module: nope
    """
    wanted = set(names)
    if unknown := wanted - set(NAMES):
        raise MsingiError(f"unknown module: {', '.join(sorted(unknown))}")
    return [module for module in MODULES if module.NAME in wanted]
