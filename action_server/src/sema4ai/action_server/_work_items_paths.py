"""Action Server validation for work-item attachment names."""

from pathlib import Path


def validate_attachment_name(name: str) -> str:
    """Validate and return one safe attachment filename component."""
    if (
        not name
        or name in {".", ".."}
        or Path(name).is_absolute()
        or "/" in name
        or "\\" in name
        or '"' in name
        or "'" in name
        or any(ord(character) < 32 for character in name)
    ):
        raise ValueError("Invalid attachment name")
    return name
