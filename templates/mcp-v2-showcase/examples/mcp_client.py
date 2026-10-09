"""Minimal stdlib client for the stateless MCP 2026-07-28 endpoint."""

from __future__ import annotations

import argparse
import json
import uuid
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

PROTOCOL_VERSION = "2026-07-28"


def post(base_url: str, method: str, params: dict | None = None) -> dict:
    request_id = str(uuid.uuid4())
    request_params = dict(params or {})
    request_params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Mcp-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
        "X-Request-ID": request_id,
    }
    if method in ("tools/call", "prompts/get"):
        headers["Mcp-Name"] = request_params["name"]
    elif method == "resources/read":
        headers["Mcp-Name"] = request_params["uri"]
    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": request_params,
    }
    request = Request(
        base_url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=10) as response:
            if response.headers.get("X-Request-ID") != request_id:
                raise RuntimeError("The response correlation ID did not match.")
            if response.headers.get("Mcp-Session-Id") is not None:
                raise RuntimeError("The stateless endpoint returned a session ID.")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"MCP request failed with HTTP {error.code}.") from None
    if "error" in payload:
        raise RuntimeError("The MCP server returned a protocol error.")
    return payload["result"]


def exercise(base_url: str) -> dict:
    """Exercise the advertised core protocol and return the observed results."""
    discovered = post(base_url, "server/discover")
    catalogs = {
        method: post(base_url, method)
        for method in (
            "tools/list",
            "resources/list",
            "resources/templates/list",
            "prompts/list",
        )
    }
    revisions = {
        result["_meta"]["actions.catalogRevision"] for result in catalogs.values()
    }
    if len(revisions) != 1:
        raise RuntimeError("Catalog responses did not share one revision.")
    for result in catalogs.values():
        if result["ttlMs"] != 0 or result["cacheScope"] != "private":
            raise RuntimeError("Catalog caching metadata did not match the contract.")
    revisions.pop()

    operations = (
        (
            "tools/call",
            {"name": "search_demo_catalog", "arguments": {"query": "guide"}},
        ),
        (
            "tools/call",
            {"name": "lookup_demo_item", "arguments": {"item_id": "alpha"}},
        ),
        (
            "resources/read",
            {"uri": "showcase://catalog/overview"},
        ),
        (
            "resources/read",
            {"uri": "showcase://items/alpha"},
        ),
        (
            "prompts/get",
            {"name": "explain_demo_item", "arguments": {"item_id": "alpha"}},
        ),
        (
            "tools/call",
            {"name": "lookup_demo_item", "arguments": {"item_id": "not-found"}},
        ),
    )
    results = [post(base_url, method, params) for method, params in operations]
    safe_error = results[-1].get("structuredContent", {})
    if safe_error.get("error") != "No demo item matches this ID.":
        raise RuntimeError("The safe demo error response did not match the contract.")
    if "not-found" in json.dumps(safe_error):
        raise RuntimeError("The safe demo error reflected its input.")
    return {"discovered": discovered, "catalogs": catalogs, "operations": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080/mcp")
    args = parser.parse_args()
    results = exercise(args.base_url)
    print("Protocol capabilities: " + json.dumps(results["discovered"], sort_keys=True))
    revisions = {
        result["_meta"]["actions.catalogRevision"]
        for result in results["catalogs"].values()
    }
    print(f"Catalog revision: {revisions.pop()} (ttlMs=0, cacheScope=private)")
    for operation in results["operations"]:
        print(json.dumps(operation, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
