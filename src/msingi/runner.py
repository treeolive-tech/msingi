# ramani: src/msingi/runner.py
"""Provision a server: the whole run, from the first check to the final summary."""

from types import ModuleType

from . import account, clipboard, modules, output, ssh, system
from .errors import MsingiError
from .modules import git_ssh
from .profiles import PROFILES
from .settings import Settings, validate
from .ssh import Connection


def provision(settings: Settings) -> None:
    """Check the input, prepare the user, run each chosen module, and print a summary.

    System modules run as the sudo user; user modules run as the target user.

    Examples::

        provision(Settings("203.0.113.10", "developer", sudo_user="ubuntu", modules=("repos",)))
    """
    selected = modules.by_name(settings.modules)
    has_system = any(module.SYSTEM for module in selected)
    has_user = any(not module.SYSTEM for module in selected)
    validate(
        settings,
        needs_sudo=has_system,
        needs_git=any(module.NAME == "git-ssh" for module in selected),
    )

    admin = Connection(
        settings.host,
        settings.sudo_user or settings.target_user,
        settings.port,
        settings.key,
    )
    target = ssh.as_user(admin, settings.target_user)

    announce(settings, selected)
    ssh.check_connection(admin)
    account.ensure_user(admin, settings)

    if has_system:
        update_package_lists(admin, settings)
    if has_user and not settings.dry_run:
        ssh.check_connection(
            target, hint=f"Pass --public-key so msingi can log in as {target.user}."
        )

    for module in selected:
        run_module(module, admin if module.SYSTEM else target, settings)

    show_summary(settings, selected, target)


def announce(settings: Settings, selected: list[ModuleType]) -> None:
    """Print the profile and which modules will run.

    Examples::

        announce(settings, selected)  # 📋 Selected Profile: Full Development Server
    """
    output.step(f"📋 Selected Profile: {PROFILES[settings.profile][0]}")
    if settings.dry_run:
        output.warn("DRY RUN MODE ENABLED - No changes will be made")
    system_names = [module.NAME for module in selected if module.SYSTEM]
    user_names = [module.NAME for module in selected if not module.SYSTEM]
    output.step(f"System modules: {', '.join(system_names) or 'none'}")
    output.step(f"User modules: {', '.join(user_names) or 'none'}")


def update_package_lists(conn: Connection, settings: Settings) -> None:
    """Run ``apt-get update`` once, before the system modules.

    Examples::

        update_package_lists(admin, settings)  # 🔄 Running apt-get update...
    """
    if settings.dry_run:
        output.dry("run apt-get update")
        return
    output.step("🔄 Running apt-get update...")
    system.apt_update(conn)


def run_module(module: ModuleType, conn: Connection, settings: Settings) -> None:
    """Run one module on ``conn``, or just say so on a dry run.

    Examples::

        run_module(nginx, admin, settings)  # 🚀 Setting up Nginx...
    """
    if settings.dry_run:
        output.dry(f"set up {module.TITLE}")
        return
    output.step(f"🚀 Setting up {module.TITLE}...")
    module.setup(conn, settings)
    output.ok(f"{module.TITLE} setup completed")


def show_summary(
    settings: Settings, selected: list[ModuleType], target: Connection
) -> None:
    """Print what was done, including the new Git public key when there is one.

    Examples::

        show_summary(settings, selected, target)  # ✅ Setup completed successfully!
    """
    print()
    if settings.dry_run:
        output.warn(
            "Dry run completed: this was a simulation, nothing on the server changed"
        )
    else:
        output.ok("Setup completed successfully!")

    sudo = "not changed"
    if settings.make_user_sudo:
        sudo = "would be granted" if settings.dry_run else "granted by this run"
    print(f"Profile:           {PROFILES[settings.profile][0]}")
    print(f"User:              {settings.target_user}")
    print(f"Passwordless sudo: {sudo}")

    if settings.dry_run or not any(module.NAME == "git-ssh" for module in selected):
        return
    key = git_ssh.public_key(target)
    print()
    print("🔑 SSH public key (add it to GitHub, GitLab or wherever you host code):")
    print(key)
    print(
        f"The private key stays on the server at ~{settings.target_user}/.ssh/id_ed25519"
    )
    if settings.copy_key:
        copy_key(key)


def copy_key(key: str) -> None:
    """Put the public key on the clipboard; a failure only warns, the key is printed above.

    Examples::

        copy_key("ssh-ed25519 AAAA... ada@example.com")  # ✅ Public key copied to the clipboard
    """
    try:
        clipboard.copy(key)
    except MsingiError as err:
        output.warn(f"Could not copy the key: {err}")
    else:
        output.ok("Public key copied to the clipboard")
