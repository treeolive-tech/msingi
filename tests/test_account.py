# ramani: tests/test_account.py
"""Creating the user, sudo access and authorized keys."""

from dataclasses import replace

from msingi import account

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEx ada@laptop"
PASSWD = "developer:x:1001:1001::/home/developer:/bin/bash\n"


def test_existing_user_is_left_alone(server, settings, admin):
    account.ensure_user(admin, settings)
    assert not server.ran("useradd")


def test_missing_user_is_created_with_sudo(server, settings, admin):
    server.when("id developer", returncode=1)
    account.ensure_user(admin, settings)
    call = server.find("useradd")
    assert call.text == "useradd -m -s /bin/bash developer"
    assert call.sudo


def test_dry_run_changes_nothing(server, settings, admin, capsys):
    server.when("id developer", returncode=1)
    dry = replace(settings, dry_run=True, make_user_sudo=True, ssh_public_key=KEY)
    account.ensure_user(admin, dry)

    assert [call.text for call in server.calls] == ["id developer"]
    out = capsys.readouterr().out
    assert "[DRY RUN] Would create user: developer" in out
    assert "[DRY RUN] Would grant sudo privileges to: developer" in out
    assert "[DRY RUN] Would add SSH public key for developer" in out


def test_passwordless_sudo_is_written_to_sudoers(server, settings, admin):
    account.ensure_user(admin, replace(settings, make_user_sudo=True))
    assert server.ran("usermod -aG sudo developer")
    assert server.find("tee /etc/sudoers.d/developer").input == "developer ALL=(ALL) NOPASSWD:ALL\n"
    assert server.ran("chmod 440 /etc/sudoers.d/developer")


def test_sudo_is_not_touched_unless_asked(server, settings, admin):
    account.ensure_user(admin, settings)
    assert not server.ran("usermod")
    assert not server.ran("sudoers")


def test_public_key_is_appended_and_permissions_fixed(server, settings, admin):
    server.when("getent passwd developer", stdout=PASSWD)
    server.when("cat /home/developer/.ssh/authorized_keys", returncode=1)
    account.ensure_user(admin, replace(settings, ssh_public_key=KEY))

    assert server.find("tee -a /home/developer/.ssh/authorized_keys").input == KEY + "\n"
    assert server.ran("chmod 700 /home/developer/.ssh")
    assert server.ran("chmod 600 /home/developer/.ssh/authorized_keys")
    assert server.ran("chown -R developer:developer /home/developer/.ssh")


def test_public_key_already_present_is_not_added_twice(server, settings, admin):
    server.when("getent passwd developer", stdout=PASSWD)
    server.when("cat /home/developer", stdout=f"ssh-rsa OTHER\n{KEY}\n")
    account.ensure_user(admin, replace(settings, ssh_public_key=KEY))
    assert not server.ran("tee -a")


def test_key_is_put_on_its_own_line_after_a_file_without_newline(server, settings, admin):
    server.when("getent passwd developer", stdout=PASSWD)
    server.when("cat /home/developer", stdout="ssh-rsa OTHER")
    account.ensure_user(admin, replace(settings, ssh_public_key=KEY))
    assert server.find("tee -a").input == "\n" + KEY + "\n"
