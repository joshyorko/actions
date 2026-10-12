from actions import mcp

UI_URI = "ui://fixture/view"

@mcp.resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {"connectDomains": ["https://api.example.test"]}}},
)
def app_view() -> str:
    return "<html>fixture</html>"

@mcp.tool(meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}, "com.example.extra": {"v": 1}})
def text_result() -> str:
    return "ready"

@mcp.tool(meta={"ui": {"resourceUri": UI_URI, "visibility": ["app"]}})
def object_result() -> dict[str, str]:
    return {"status": "ready"}
