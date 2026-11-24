# ramani: src/msingi/clipboard.py
"""Copy text to the clipboard with pyperclip."""

from .errors import MsingiError


def copy(text: str) -> None:
    """Copy ``text``; raises MsingiError with a readable reason on failure.

    On Linux the clipboard needs ``xclip``, ``xsel`` or ``wl-clipboard`` installed.

    Examples::

        copy("ssh-ed25519 AAAAC3Nz... ada@example.com")  # None
        copy("text")  # MsingiError: no clipboard available: ...
    """
    try:
        import pyperclip  # only needed when --copy is used
    except ImportError:
        raise MsingiError("pyperclip is not installed (uv add pyperclip)") from None
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as err:
        raise MsingiError(f"no clipboard available: {err}") from None
