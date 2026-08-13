import json
import asyncio
import uuid

from actions.server.mcp.gateway_metadata import (
    MCP_CORRELATION_ID_HEADER,
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_REQUEST_STATE_KEY,
    MCP_CORRELATION_ID_ATTRIBUTE,
    MCP_METHOD_ATTRIBUTE,
    MCP_NAME_ATTRIBUTE,
    McpRequestMetadataMiddleware,
    get_mcp_request_metadata,
)


def _request(body, headers=None):
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            *[(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
        ],
        "state": {},
        "body": json.dumps(body).encode(),
    }


async def _run(body, headers=None, authenticated=True):
    seen = {}

    async def app(scope, receive, send):
        seen["state"] = scope["state"]
        seen["context"] = get_mcp_request_metadata()
        seen["authenticated"] = authenticated
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = McpRequestMetadataMiddleware(app)
    sent = []

    async def receive():
        return {"type": "http.request", "body": _request(body, headers)["body"]}

    async def send(message):
        sent.append(message)

    await middleware(_request(body, headers), receive, send)
    return seen, sent


def test_exposes_validated_tool_identity_to_state_and_context():
    seen, sent = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "greet"}},
        {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "greet"},
    ))

    metadata = seen["state"][MCP_REQUEST_STATE_KEY]
    assert metadata.method == "tools/call"
    assert metadata.name == "greet"
    assert seen["context"] == metadata
    assert metadata.telemetry_attributes == {
        MCP_METHOD_ATTRIBUTE: "tools/call",
        MCP_NAME_ATTRIBUTE: "greet",
        MCP_CORRELATION_ID_ATTRIBUTE: metadata.correlation_id,
    }
    assert sent[0]["status"] == 204


def test_extracts_named_resource_and_prompt_from_validated_params():
    for method, params, name in (
        ("resources/read", {"uri": "resource://greet"}, "resource://greet"),
        ("prompts/get", {"name": "friendly"}, "friendly"),
    ):
        seen, _ = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        {MCP_METHOD_HEADER: method, MCP_NAME_HEADER: name},
        ))
        metadata = seen["state"][MCP_REQUEST_STATE_KEY]
        assert (metadata.method, metadata.name) == (method, name)


def test_batch_metadata_is_bounded_and_notifications_are_supported():
    seen, _ = asyncio.run(_run(
        [
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        ],
        {MCP_METHOD_HEADER: "batch"},
    ))
    metadata = seen["state"][MCP_REQUEST_STATE_KEY]
    assert metadata.method == "batch"
    assert metadata.name is None


def test_spoofed_or_inconsistent_identity_is_rejected():
    for headers in (
        {MCP_METHOD_HEADER: "tools/list"},
        {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "other"},
        {MCP_METHOD_HEADER: "client/secret", MCP_NAME_HEADER: "arbitrary"},
    ):
        seen, sent = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "greet"}},
        headers,
        ))
        assert "state" not in seen
        assert sent[0]["status"] == 400


def test_missing_headers_are_normalized_from_body():
    seen, _ = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "greet"}}
    ))
    metadata = seen["state"][MCP_REQUEST_STATE_KEY]
    assert (metadata.method, metadata.name) == ("tools/call", "greet")


def test_correlation_id_preserves_valid_uuid_and_generates_for_arbitrary_input():
    correlation_id = str(uuid.uuid4())
    seen, _ = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {MCP_CORRELATION_ID_HEADER: correlation_id},
    ))
    assert seen["state"][MCP_REQUEST_STATE_KEY].correlation_id == correlation_id

    seen, _ = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {MCP_CORRELATION_ID_HEADER: "not-a-safe-id"},
    ))
    generated = seen["state"][MCP_REQUEST_STATE_KEY].correlation_id
    assert generated != "not-a-safe-id"
    uuid.UUID(generated)


def test_authentication_is_checked_before_metadata_parser():
    seen, sent = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "secret"}},
        {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "secret"},
        authenticated=False,
    ))
    assert seen["authenticated"] is False
    assert sent[0]["status"] == 204


def test_error_body_does_not_trust_arbitrary_headers():
    seen, sent = asyncio.run(_run(
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "bad"}},
        {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "secret"},
    ))
    assert "state" not in seen
    assert sent[0]["status"] == 400
