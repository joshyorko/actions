"""Small path-component rules shared by portable source and Robot ZIP checks."""

from __future__ import annotations

import unicodedata

_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
}
_WINDOWS_RESERVED_NAMES.update(
    f"{prefix}{digit}"
    for prefix in ("COM", "LPT")
    for digit in "123456789¹²³"
)
_WINDOWS_INVALID_CHARACTERS = frozenset('<>:"|?*')


def is_portable_path_component(component: str) -> bool:
    """Return whether a name component is safe on the Windows path model."""
    if not component or component.endswith((".", " ")):
        return False
    basename = component.split(".", 1)[0].rstrip(" ").upper()
    return not (
        basename in _WINDOWS_RESERVED_NAMES
        or any(
            character in _WINDOWS_INVALID_CHARACTERS or ord(character) < 32
            for character in component
        )
    )


def portable_path_collision_key(component: str) -> str:
    """Return the case-insensitive NFC key used for portable path collisions."""
    return unicodedata.normalize("NFC", component).casefold()
