# ramani: src/msingi/modules/nginx.py
"""Install Nginx, open it in the firewall, and add a reusable proxy snippet."""

from .. import output, ssh, system
from ..settings import Settings
from ..ssh import Connection

NAME = "nginx"
TITLE = "Nginx"
SYSTEM = True

SNIPPET_PATH = "/etc/nginx/snippets/port-proxy.conf"
SNIPPET = """\
location / {
    proxy_pass http://127.0.0.1:$upstream_port;
    include proxy_params;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_cache_bypass $http_upgrade;
}
"""


def setup(conn: Connection, settings: Settings) -> None:
    """Install Nginx, allow it in UFW, start it, write the proxy snippet and test the config.

    Examples::

        setup(conn, settings)  # ✅ Nginx is running
    """
    install(conn)
    open_firewall(conn)
    system.enable_and_start(conn, "nginx")
    output.ok("Nginx is running")
    write_snippet(conn)
    test_config(conn)


def install(conn: Connection) -> None:
    """Install Nginx unless it is already there."""
    if ssh.command_exists(conn, "nginx", sudo=True):
        output.ok("Nginx already installed")
    else:
        system.apt_install(conn, "nginx")


def open_firewall(conn: Connection) -> None:
    """Allow 'Nginx Full' (ports 80 and 443) in UFW, if UFW can be used."""
    if system.ensure_ufw(conn) and not system.ufw_has_rule(conn, "Nginx Full"):
        system.ufw_allow(conn, "Nginx Full")


def write_snippet(conn: Connection) -> None:
    """Write ``port-proxy.conf`` unless it already holds the same text.

    Examples::

        write_snippet(conn)  # ✅ Wrote /etc/nginx/snippets/port-proxy.conf
    """
    current = ssh.run(conn, ["cat", SNIPPET_PATH], sudo=True, check=False).stdout
    if current == SNIPPET:
        output.ok(f"{SNIPPET_PATH} is up to date")
        return
    ssh.run(conn, ["mkdir", "-p", "/etc/nginx/snippets"], sudo=True)
    ssh.run(conn, ["tee", SNIPPET_PATH], sudo=True, input=SNIPPET)
    output.ok(f"Wrote {SNIPPET_PATH}")


def test_config(conn: Connection) -> None:
    """Run ``nginx -t`` and warn, without failing, if the configuration is invalid."""
    if ssh.succeeds(conn, ["nginx", "-t"], sudo=True):
        output.ok("Nginx configuration is valid")
    else:
        output.warn("Nginx configuration test failed")
        output.note("You may need to check /etc/nginx/nginx.conf")
