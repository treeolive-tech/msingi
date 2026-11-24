# ramani: src/msingi/modules/repos.py
"""Make sure the target user has a ``~/repos`` folder."""

from .. import output, ssh
from ..settings import Settings
from ..ssh import Connection

NAME = "repos"
TITLE = "repos directory"
SYSTEM = False


def setup(conn: Connection, settings: Settings) -> None:
    """Create ``~/repos`` unless it exists.

    Examples::

        setup(user_conn, settings)  # ✅ Created repos directory
    """
    if ssh.succeeds(conn, 'test -d "$HOME/repos"'):
        output.ok("repos directory already exists")
        return
    ssh.run(conn, 'mkdir -p "$HOME/repos"')
    output.ok("Created repos directory")
