"""Collect the MCP runtime without importing its optional development CLI."""


def is_mcp_runtime_module(name: str) -> bool:
    return name != "mcp.cli" and not name.startswith("mcp.cli.")
