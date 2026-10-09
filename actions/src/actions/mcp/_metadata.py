"""Validation and snapshotting for public MCP ``_meta`` declarations."""

from __future__ import annotations

import json
import math
from urllib.parse import urlsplit

MAX_MCP_META_BYTES = 64 * 1024
MAX_MCP_META_DEPTH = 16
_MCP_APP_CSP_FIELDS = {
    "connectDomains",
    "resourceDomains",
    "frameDomains",
    "baseUriDomains",
}
_MCP_APP_VISIBILITIES = {"model", "app"}
_MCP_APP_RESOURCE_MIME = "text/html;profile=mcp-app"


def _is_ui_resource_uri(value: object) -> bool:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return parsed.scheme == "ui" and parsed.hostname is not None


def _uses_ui_scheme(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return urlsplit(value).scheme == "ui"
    except ValueError:
        return value[:3].lower() == "ui:"


def _validate_app_fields(meta: dict, *, subject: str) -> None:
    if "ui" not in meta:
        return
    ui = meta["ui"]
    if not isinstance(ui, dict):
        raise ValueError(f"MCP {subject} metadata 'ui' must be an object")

    if "resourceUri" in ui and not _is_ui_resource_uri(ui["resourceUri"]):
        raise ValueError(
            f"MCP {subject} metadata 'ui.resourceUri' must be a valid ui:// URI"
        )

    if "visibility" in ui:
        visibility = ui["visibility"]
        if (
            not isinstance(visibility, list)
            or any(
                not isinstance(item, str) or item not in _MCP_APP_VISIBILITIES
                for item in visibility
            )
            or len(visibility) != len(set(visibility))
        ):
            raise ValueError(
                f"MCP {subject} metadata 'ui.visibility' must contain unique 'model' and/or 'app' values"
            )

    if "csp" in ui:
        csp = ui["csp"]
        if not isinstance(csp, dict) or csp.keys() - _MCP_APP_CSP_FIELDS:
            raise ValueError(
                f"MCP {subject} metadata 'ui.csp' must contain only supported CSP domain fields"
            )
        for field, domains in csp.items():
            if not isinstance(domains, list) or any(
                not isinstance(domain, str) or not domain for domain in domains
            ):
                raise ValueError(
                    f"MCP {subject} metadata 'ui.csp.{field}' must be a list of non-empty strings"
                )


def normalize_mcp_meta(meta: object, *, subject: str) -> dict | None:
    """Return a bounded detached JSON object suitable for MCP ``_meta``."""
    if meta is None:
        return None
    if not isinstance(meta, dict):
        raise ValueError(f"MCP {subject} metadata must be an object")

    active_containers: set[int] = set()
    encoded_size = 2  # Top-level object braces.

    def add_size(size: int) -> None:
        nonlocal encoded_size
        encoded_size += size
        if encoded_size > MAX_MCP_META_BYTES:
            raise ValueError(
                f"MCP {subject} metadata exceeds {MAX_MCP_META_BYTES} encoded bytes"
            )

    def encoded_string_size(value: str) -> int:
        size = 2  # JSON string quotes.
        short_escapes = {'"': 2, "\\": 2, "\b": 2, "\f": 2, "\n": 2, "\r": 2, "\t": 2}
        for character in value:
            codepoint = ord(character)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise ValueError(
                    f"MCP {subject} metadata strings must be valid Unicode"
                )
            if character in short_escapes:
                size += short_escapes[character]
            elif codepoint < 0x20:
                size += 6  # JSON \u00XX escape.
            elif codepoint <= 0x7F:
                size += 1
            elif codepoint <= 0x7FF:
                size += 2
            elif codepoint <= 0xFFFF:
                size += 3
            else:
                size += 4
            if encoded_size + size > MAX_MCP_META_BYTES:
                raise ValueError(
                    f"MCP {subject} metadata exceeds {MAX_MCP_META_BYTES} encoded bytes"
                )
        return size

    def validate_json(value: object, depth: int) -> None:
        if depth > MAX_MCP_META_DEPTH:
            raise ValueError(f"MCP {subject} metadata exceeds maximum nesting depth")
        if isinstance(value, dict):
            identity = id(value)
            if identity in active_containers:
                raise ValueError(f"MCP {subject} metadata must not contain cycles")
            active_containers.add(identity)
            try:
                for index, (key, item) in enumerate(value.items()):
                    if index:
                        add_size(1)
                    if not isinstance(key, str):
                        raise ValueError(
                            f"MCP {subject} metadata object keys must be strings"
                        )
                    validate_json(key, depth + 1)
                    add_size(1)  # Colon between key and value.
                    validate_json(item, depth + 1)
                if identity != id(meta):
                    add_size(2)  # Nested object braces.
            finally:
                active_containers.remove(identity)
        elif isinstance(value, list):
            identity = id(value)
            if identity in active_containers:
                raise ValueError(f"MCP {subject} metadata must not contain cycles")
            active_containers.add(identity)
            try:
                for index, item in enumerate(value):
                    if index:
                        add_size(1)
                    validate_json(item, depth + 1)
                add_size(2)  # Array brackets.
            finally:
                active_containers.remove(identity)
        elif isinstance(value, str):
            add_size(encoded_string_size(value))
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"MCP {subject} metadata numbers must be finite")
        elif value is None or type(value) in (bool, int, float):
            add_size(len(json.dumps(value, allow_nan=False)))
            return
        else:
            raise ValueError(f"MCP {subject} metadata must contain only JSON values")

    validate_json(meta, 0)
    serialized = json.dumps(
        meta, allow_nan=False, ensure_ascii=False, separators=(",", ":")
    )
    if len(serialized.encode("utf-8")) > MAX_MCP_META_BYTES:
        raise ValueError(
            f"MCP {subject} metadata exceeds {MAX_MCP_META_BYTES} encoded bytes"
        )
    snapshot = json.loads(serialized)
    _validate_app_fields(snapshot, subject=subject)
    return snapshot


def validate_ui_resource_declaration(
    uri: str, mime_type: str | None, meta: dict | None
) -> None:
    """Check the public MCP Apps resource identity and metadata contract."""
    is_ui_uri = _is_ui_resource_uri(uri)
    if _uses_ui_scheme(uri) and not is_ui_uri:
        raise ValueError("MCP Apps resource URI must be a valid ui:// URI")
    if is_ui_uri:
        if mime_type != _MCP_APP_RESOURCE_MIME:
            raise ValueError(
                f"MCP Apps resource {uri!r} must use MIME type {_MCP_APP_RESOURCE_MIME!r}"
            )
    if meta is not None and "ui" in meta:
        if not is_ui_uri:
            raise ValueError("MCP Apps resource metadata requires a ui:// URI")
        if mime_type != _MCP_APP_RESOURCE_MIME:
            raise ValueError(
                f"MCP Apps resource {uri!r} must use MIME type {_MCP_APP_RESOURCE_MIME!r}"
            )
