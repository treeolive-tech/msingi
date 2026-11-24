# ramani: src/msingi/errors.py
"""The one error type msingi shows as a plain message instead of a traceback."""


class MsingiError(Exception):
    """A problem the user can fix, such as bad input or a failed command on the server."""
