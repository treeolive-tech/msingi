# ramani: tests/test_modules.py
"""Each module on a fake server: what it does on a bare server, and what it skips when done."""

from dataclasses import replace

import pytest

from msingi.errors import MsingiError
from msingi.modules import (
    certbot,
    git_ssh,
    nginx,
    nvm,
    openssh_ufw,
    packages,
    postgres,
    repos,
    uv,
)

ACTIVE_WITH_SSH = "Status: active\nOpenSSH    ALLOW    Anywhere\n"
INACTIVE = "Status: inactive\n"


# openssh-ufw


def test_ufw_is_installed_allowed_and_enabled_on_a_bare_server(server, settings, admin):
    server.when("command -v ufw", returncode=1)
    server.when("ufw status", stdout=(INACTIVE, INACTIVE + "OpenSSH    ALLOW    Anywhere\n"))
    openssh_ufw.setup(admin, settings)
    assert server.ran("apt-get install -y ufw")
    assert server.ran("ufw allow OpenSSH")
    assert server.ran("ufw --force enable")


def test_ufw_is_left_alone_when_already_set_up(server, settings, admin):
    server.when("ufw status", stdout=ACTIVE_WITH_SSH)
    openssh_ufw.setup(admin, settings)
    assert not server.ran("ufw allow")
    assert not server.ran("--force enable")


def test_ufw_is_never_enabled_without_a_confirmed_ssh_rule(server, settings, admin):
    server.when("ufw status", stdout=INACTIVE)
    with pytest.raises(MsingiError, match="not confirmed"):
        openssh_ufw.setup(admin, settings)
    assert not server.ran("--force enable")


def test_ufw_also_allows_a_custom_ssh_port(server, settings, admin):
    server.when("ufw status", stdout=ACTIVE_WITH_SSH)
    openssh_ufw.setup(admin, replace(settings, port=2222))
    assert server.ran("ufw allow 2222/tcp")


def test_ufw_install_failure_skips_the_module(server, settings, admin):
    server.when("command -v ufw", returncode=1)
    server.when("apt-get install", returncode=100)
    openssh_ufw.setup(admin, settings)
    assert not server.ran("ufw allow")


# packages


def test_packages_are_installed_in_one_apt_call(server, settings, admin):
    packages.setup(admin, settings)
    call = server.find("apt-get install")
    assert call.sudo
    assert all(name in call.text for name in ("git", "snapd", "pandoc", "texlive-xetex"))


# nginx


def test_nginx_is_installed_started_and_given_the_snippet(server, settings, admin):
    server.when("command -v nginx", returncode=1)
    server.when("systemctl is-enabled", returncode=1)
    server.when("systemctl is-active", returncode=1)
    server.when("cat /etc/nginx", returncode=1)
    nginx.setup(admin, settings)
    assert server.ran("apt-get install -y nginx")
    assert server.ran("ufw allow 'Nginx Full'")
    assert server.ran("systemctl enable nginx")
    assert server.ran("systemctl start nginx")
    assert server.find("tee /etc/nginx/snippets/port-proxy.conf").input == nginx.SNIPPET


def test_nginx_done_is_left_alone(server, settings, admin):
    server.when("cat /etc/nginx", stdout=nginx.SNIPPET)
    server.when("ufw status", stdout="Nginx Full    ALLOW    Anywhere\n")
    nginx.setup(admin, settings)
    for fragment in ("apt-get", "systemctl enable", "systemctl start", "tee", "ufw allow"):
        assert not server.ran(fragment)


def test_nginx_snippet_is_rewritten_when_it_differs(server, settings, admin):
    server.when("cat /etc/nginx", stdout="old\n")
    nginx.setup(admin, settings)
    assert server.ran("tee /etc/nginx/snippets/port-proxy.conf")


def test_nginx_config_failure_only_warns(server, settings, admin, capsys):
    server.when("nginx -t", returncode=1)
    nginx.setup(admin, settings)
    assert "Nginx configuration test failed" in capsys.readouterr().out


# certbot


def test_certbot_needs_snapd(server, settings, admin):
    server.when("command -v snap", returncode=1)
    with pytest.raises(MsingiError, match="snapd is not installed"):
        certbot.setup(admin, settings)


def test_certbot_already_installed_does_nothing(server, settings, admin):
    certbot.setup(admin, settings)
    assert not server.ran("snap install")


def test_certbot_is_installed_through_snap(server, settings, admin):
    server.when("snap list certbot", returncode=1)
    certbot.setup(admin, settings)
    assert server.ran("snap install core")
    assert server.ran("apt-get remove -y certbot")
    assert server.ran("snap install --classic certbot")
    assert server.ran("ln -sf /snap/bin/certbot /usr/bin/certbot")


# postgres


def test_postgres_is_installed_and_started(server, settings, admin):
    server.when("command -v psql", returncode=1)
    server.when("systemctl is-enabled", returncode=1)
    server.when("systemctl is-active", returncode=1)
    postgres.setup(admin, settings)
    assert server.ran("apt-get install -y postgresql postgresql-contrib libpq-dev")
    assert server.ran("systemctl enable postgresql")
    assert server.ran("systemctl start postgresql")


def test_postgres_done_is_left_alone(server, settings, admin):
    postgres.setup(admin, settings)
    assert not server.ran("apt-get")
    assert not server.ran("systemctl enable")


# uv


def test_uv_and_python_are_installed_on_a_bare_user(server, settings, user_conn):
    server.when("test -x", returncode=1)
    uv.setup(user_conn, settings)
    assert server.ran("curl -LsSf https://astral.sh/uv/install.sh | sh")
    assert server.ran("python install")


def test_uv_only_counts_pythons_that_uv_manages(server, settings, user_conn):
    """The system Python must not count: Ubuntu always has one."""
    uv.setup(user_conn, settings)
    listing = server.find("python list")
    assert "--only-installed" in listing.text
    assert "--managed-python" in listing.text
    assert server.ran("python install")


def test_uv_and_python_already_there_are_skipped(server, settings, user_conn):
    server.when("python list --only-installed", stdout="cpython-3.13.1-linux-x86_64\n")
    uv.setup(user_conn, settings)
    assert not server.ran("curl")
    assert not server.ran("python install")


def test_uv_python_failure_only_gives_a_hint(server, settings, user_conn, capsys):
    server.when("python install", returncode=1)
    uv.setup(user_conn, settings)
    assert "uv python install" in capsys.readouterr().out


# nvm


def test_nvm_node_and_npm_are_installed_on_a_bare_user(server, settings, user_conn):
    server.when("test -d", returncode=1)
    server.when("nvm version node", stdout="N/A\n")
    nvm.setup(user_conn, settings)
    assert server.ran("nvm-sh/nvm/v0.40.4/install.sh | bash")
    assert server.ran("nvm install node")
    assert server.ran("npm install -g npm@latest")


def test_nvm_version_comes_from_the_settings(server, settings, user_conn):
    server.when("test -d", returncode=1)
    nvm.setup(user_conn, replace(settings, nvm_version="v0.39.7"))
    assert server.ran("nvm-sh/nvm/v0.39.7/install.sh")


def test_nvm_with_node_installed_is_skipped(server, settings, user_conn):
    server.when("nvm version node", stdout="v22.1.0\n")
    nvm.setup(user_conn, settings)
    assert not server.ran("curl")
    assert not server.ran("nvm install node")


def test_nvm_missing_script_gives_a_hint(server, settings, user_conn, capsys):
    server.when('test -s "$HOME/.nvm/nvm.sh"', returncode=1)
    nvm.setup(user_conn, settings)
    out = capsys.readouterr().out
    assert "nvm.sh not found" in out
    assert not server.ran("nvm install node")


def test_nvm_node_failure_only_warns(server, settings, user_conn, capsys):
    server.when("nvm version node", stdout="N/A\n")
    server.when("nvm install node", returncode=1)
    nvm.setup(user_conn, settings)
    assert "Failed to install Node.js" in capsys.readouterr().out
    assert not server.ran("npm install")


# repos


def test_repos_dir_is_created_when_missing(server, settings, user_conn):
    server.when("test -d", returncode=1)
    repos.setup(user_conn, settings)
    assert server.ran('mkdir -p "$HOME/repos"')


def test_repos_dir_that_exists_is_left_alone(server, settings, user_conn):
    repos.setup(user_conn, settings)
    assert not server.ran("mkdir")


# git-ssh


def test_git_is_configured_and_a_key_is_made(server, settings, user_conn):
    server.when('test -f "$HOME/.ssh/id_ed25519"', returncode=1)
    server.when('test -f "$HOME/.ssh/config"', returncode=1)
    git_ssh.setup(user_conn, settings)
    assert server.ran("git config --global user.name 'Ada Lovelace'")
    assert server.ran("git config --global user.email ada@example.com")
    assert server.ran("ssh-keygen -t ed25519 -C ada@example.com -N \"\"")
    assert server.ran('touch "$HOME/.ssh/config"')


def test_git_existing_key_and_config_are_kept(server, settings, user_conn):
    git_ssh.setup(user_conn, settings)
    assert not server.ran("ssh-keygen -t")
    assert not server.ran("touch")


def test_git_needs_its_tools(server, settings, user_conn):
    server.when("command -v ssh-keygen", returncode=1)
    with pytest.raises(MsingiError, match="ssh-keygen command not found"):
        git_ssh.setup(user_conn, settings)


def test_public_key_is_read_back(server, user_conn):
    server.when("id_ed25519.pub", stdout="ssh-ed25519 AAAA ada@example.com\n")
    assert git_ssh.public_key(user_conn) == "ssh-ed25519 AAAA ada@example.com"
