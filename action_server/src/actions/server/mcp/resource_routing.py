"""Retain admitted resource winners without changing the template language."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

import rfc8785

if TYPE_CHECKING:
    from actions.server._database import Database

MATCHER_POLICY_VERSION = 1
MAX_PROJECTIONS = 256
MAX_ROUTE_ROWS = 10_000
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
_DIGEST_DOMAIN = b"actions.mcp.resource-routing.v1\0"
Route = tuple[str, str, str]
Identity = tuple[str, str]


def resource_template_matches(template: str, uri: str) -> dict[str, Any] | None:
    # Preserve the existing anchored substitution, including unescaped literals.
    pattern = template.replace("{", "(?P<").replace("}", ">[^/]+)")
    match = re.match(f"^{pattern}$", uri)
    return match.groupdict() if match else None


@dataclass(frozen=True)
class ResourceRoutingProjection:
    resources: tuple[Route, ...]
    templates: tuple[Route, ...]

    def owner(self, uri: str) -> Identity | None:
        for key, package, action in self.resources:
            if key == uri:
                return package, action
        for template, package, action in self.templates:
            if resource_template_matches(template, uri):
                return package, action
        return None

    @property
    def row_count(self) -> int:
        return len(self.resources) + len(self.templates)

    def encode(self) -> bytes:
        return rfc8785.dumps(
            {
                "matcherPolicyVersion": MATCHER_POLICY_VERSION,
                "resources": self.resources,
                "templates": self.templates,
            }
        )


def _decode(payload: bytes) -> ResourceRoutingProjection:
    try:
        value = json.loads(payload)
        if (
            not isinstance(value, dict)
            or set(value) != {"matcherPolicyVersion", "resources", "templates"}
            or not isinstance(value["matcherPolicyVersion"], int)
            or isinstance(value["matcherPolicyVersion"], bool)
            or value["matcherPolicyVersion"] != MATCHER_POLICY_VERSION
        ):
            raise ValueError("unsupported matcher policy or projection fields")
        groups = []
        for name in ("resources", "templates"):
            rows = value[name]
            if not isinstance(rows, list) or len(rows) > MAX_ROUTE_ROWS:
                raise ValueError("invalid route rows")
            result = []
            for row in rows:
                if (
                    not isinstance(row, list)
                    or len(row) != 3
                    or not all(isinstance(item, str) for item in row)
                    or not row[0]
                ):
                    raise ValueError("invalid route identity")
                is_template = "{" in row[0] and "}" in row[0]
                if is_template != (name == "templates"):
                    raise ValueError("invalid route kind")
                if is_template:
                    pattern = row[0].replace("{", "(?P<").replace("}", ">[^/]+)")
                    re.compile(f"^{pattern}$")
                result.append(tuple(row))
            if result != sorted(result) or len({row[0] for row in result}) != len(
                result
            ):
                raise ValueError("routes must have distinct, sorted keys")
            groups.append(tuple(result))
        projection = ResourceRoutingProjection(*groups)
        if not projection.row_count or projection.encode() != payload:
            raise ValueError("empty or noncanonical projection")
        return projection
    except (ValueError, TypeError, UnicodeError, RecursionError, re.error) as exc:
        raise ValueError(f"Invalid MCP resource-routing history: {exc}") from exc


def reserve_resource_routing(
    db: "Database", resources: list[Route], templates: list[Route]
) -> tuple[ResourceRoutingProjection, ...]:
    """Validate/append history under the existing catalog admission transaction.

    The caller holds the SQLite writer or PostgreSQL catalog table lock. Bounds
    limit stored bytes and route iterations, not arbitrary regex execution time.
    Protective history is never evicted or reinterpreted on version mismatch.
    """
    from actions.server._models import McpResourceRouting

    assert db.in_transaction()
    byte_length = (
        "octet_length(routing_json)"
        if db.backend_name == "postgresql"
        else "length(CAST(routing_json AS BLOB))"
    )
    with db.cursor() as cursor:
        db.execute_query(
            cursor,
            f"SELECT COUNT(*), COALESCE(SUM({byte_length}), 0) FROM mcp_resource_routing",
        )
        count, stored_bytes = cursor.fetchone()
    if count > MAX_PROJECTIONS or stored_bytes > MAX_PAYLOAD_BYTES:
        raise ValueError(
            "MCP resource-routing history exceeds capacity; admission rejected."
        )
    history = []
    bindings = {}
    route_rows = 0
    for binding in db.all(McpResourceRouting, order_by="id"):
        payload = binding.routing_json.encode("utf-8")
        projection = _decode(payload)
        if sha256(_DIGEST_DOMAIN + payload).hexdigest() != binding.id:
            raise ValueError(
                "MCP resource-routing history digest mismatch; admission rejected."
            )
        route_rows += projection.row_count
        if route_rows > MAX_ROUTE_ROWS:
            raise ValueError(
                "MCP resource-routing history exceeds route capacity; admission rejected."
            )
        bindings[binding.id] = payload
        history.append(projection)

    if len(resources) + len(templates) > MAX_ROUTE_ROWS:
        raise ValueError(
            "MCP resource-routing candidate exceeds route capacity; admission rejected."
        )
    if not resources and not templates:
        return tuple(history)
    candidate = ResourceRoutingProjection(
        tuple(sorted(resources)), tuple(sorted(templates))
    )
    payload = candidate.encode()
    key = sha256(_DIGEST_DOMAIN + payload).hexdigest()
    if key in bindings:
        if bindings[key] != payload:
            raise ValueError(
                "MCP resource-routing digest collision; admission rejected."
            )
        return tuple(history)
    if (
        count + 1 > MAX_PROJECTIONS
        or route_rows + candidate.row_count > MAX_ROUTE_ROWS
        or stored_bytes + len(payload) > MAX_PAYLOAD_BYTES
    ):
        raise ValueError(
            "MCP resource-routing history capacity reached; admission rejected. "
            "Protective history cannot be evicted. Retain the last-good catalog."
        )
    # Apply exactly the same canonical/shape/matcher checks to new and old rows.
    candidate = _decode(payload)
    db.insert(McpResourceRouting(key, payload.decode("utf-8")))
    history.append(candidate)
    return tuple(history)
