# ramani: src/msingi/cli.py
"""Command-line interface."""

import argparse
import os
from pathlib import Path

from . import output, runner
from .errors import MsingiError
from .modules import MODULES
from .profiles import PROFILES, choose
from .settings import DEFAULT_NVM_VERSION, KEY_PREFIXES, Settings


def _version() -> str:
    """Return the installed version, or "unknown" if msingi isn't installed.

    Examples::

        _version()  # "0.1.0"
    """
    from importlib.metadata import (
        PackageNotFoundError,
        version,
    )  # slow, only needed here

    try:
        return version("msingi")
    except PackageNotFoundError:
        return "unknown"


def _epilog() -> str:
    """List the profiles and modules for ``--help``."""
    profiles = "\n".join(f"  {name:<8}{label}" for name, (label, _) in PROFILES.items())
    names = "\n".join(
        f"  {module.NAME:<12}{'system (sudo)' if module.SYSTEM else 'user':<15}{module.TITLE}"
        for module in MODULES
    )
    return f"profiles (--profile):\n{profiles}\n\nmodules (--modules):\n{names}"


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        prog="msingi",
        description="Lay the foundation of an Ubuntu server over SSH: pick a profile and only the modules you chose are set up.",
        epilog=_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("host", help="server IP address or hostname")
    p.add_argument("user", help="user to set up (created if it doesn't exist)")
    p.add_argument("-p", "--port", type=int, default=22, help="SSH port (default: 22)")
    p.add_argument(
        "-k",
        "--key",
        type=Path,
        default=os.environ.get("MSINGI_SSH_KEY"),
        metavar="FILE",
        help="private key to log in with (also MSINGI_SSH_KEY; default: ssh's own keys and agent)",
    )
    p.add_argument(
        "-s",
        "--sudo-user",
        default=os.environ.get("MSINGI_SUDO_USER"),
        metavar="USER",
        help="existing user with passwordless sudo, used for system modules (also MSINGI_SUDO_USER)",
    )
    p.add_argument(
        "--make-sudo",
        action="store_true",
        help="give the user passwordless sudo (new or existing)",
    )
    p.add_argument(
        "--public-key",
        metavar="KEY_OR_FILE",
        help="public key (or a .pub file) to add to the user's authorized_keys",
    )
    p.add_argument(
        "-P",
        "--profile",
        choices=list(PROFILES),
        help="what to set up (default: full)",
    )
    p.add_argument(
        "-m",
        "--modules",
        metavar="NAME[,NAME...]",
        help="set up only these modules (custom profile)",
    )
    p.add_argument("--git-name", metavar="NAME", help="Git user name (git-ssh module)")
    p.add_argument(
        "--git-email", metavar="EMAIL", help="Git user email (git-ssh module)"
    )
    p.add_argument(
        "--nvm-version",
        default=os.environ.get("MSINGI_NVM_VERSION", DEFAULT_NVM_VERSION),
        metavar="TAG",
        help=f"nvm release to install (default: {DEFAULT_NVM_VERSION}; also MSINGI_NVM_VERSION)",
    )
    p.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="copy the new Git public key to your clipboard (git-ssh module)",
    )
    p.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="show what would happen, change nothing on the server",
    )
    p.add_argument("-V", "--version", action="version", version=f"msingi {_version()}")
    return p


def read_public_key(value: str) -> str:
    """Accept a public key as text or as the path of a ``.pub`` file.

    Examples::

        read_public_key("ssh-ed25519 AAAA... ada@laptop")  # same text
        read_public_key("~/.ssh/id_ed25519.pub")  # the file's contents
    """
    value = value.strip()
    if not value or value.startswith(KEY_PREFIXES):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        raise MsingiError(f"public key file not found: {value}")
    return path.read_text(encoding="utf-8").strip()


def build_settings(args: argparse.Namespace) -> Settings:
    """Turn parsed arguments into ``Settings``.

    Examples::

        build_settings(_parser().parse_args(["203.0.113.10", "dev", "-m", "nginx"]))
    """
    names = [name.strip() for name in (args.modules or "").split(",") if name.strip()]
    profile, modules = choose(args.profile, names)
    return Settings(
        host=args.host,
        target_user=args.user,
        port=args.port,
        key=args.key.expanduser() if args.key else None,
        sudo_user=args.sudo_user or "",
        make_user_sudo=args.make_sudo,
        ssh_public_key=read_public_key(args.public_key or ""),
        profile=profile,
        modules=modules,
        git_user_name=args.git_name or "",
        git_user_email=args.git_email or "",
        nvm_version=args.nvm_version,
        copy_key=args.copy,
        dry_run=args.dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        settings = build_settings(args)
    except MsingiError as err:
        parser.error(str(err))

    try:
        runner.provision(settings)
    except MsingiError as err:
        output.fail(f"msingi: {err}")
        return 1
    except KeyboardInterrupt:
        output.fail("msingi: interrupted")
        return 130
    return 0
