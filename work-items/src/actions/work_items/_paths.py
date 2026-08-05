"""Safe filesystem path helpers for work item attachments."""

from pathlib import Path


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def validate_attachment_name(name: str) -> str:
    """Validate and return a single safe attachment filename."""
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


def resolve_item_directory(storage_root: Path, item_id: str) -> Path:
    """Resolve an item directory and ensure it remains under storage_root."""
    root = storage_root.resolve()
    candidate = (root / item_id).resolve()
    if not _is_within(root, candidate):
        raise ValueError("Invalid work item ID")
    return candidate


def resolve_attachment_path(item_root: Path, name: str) -> Path:
    """Resolve an attachment path and ensure it remains under item_root."""
    filename = validate_attachment_name(name)
    root = item_root.resolve()
    candidate = (root / filename).resolve()
    if not _is_within(root, candidate):
        raise ValueError("Invalid attachment path")
    return candidate
