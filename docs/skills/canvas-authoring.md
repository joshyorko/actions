# Canvas authoring

This guide covers the public MCP Apps Canvas path used by
[`templates/canvas-mail-chat`](../../templates/canvas-mail-chat/README.md).
Declare the HTML view with `actions.mcp.resource` at a stable `ui://` URI and
`text/html;profile=mcp-app`; attach it to the tool with
`meta={"ui": {"resourceUri": ..., "visibility": ["model", "app"]}}`.
The Action Server serves that resource and preserves the tool's MCP result.

Return a useful string from the attached tool when callers may not display the
Canvas. The Action Server's public MCP test verifies that a string result is
returned as a text content block, while a dictionary result is returned as
`structuredContent` with no text block. A text-first client such as T3 can use
that string as its fallback without invoking a separate renderer.

Build both presentations from one normalized data source. The Canvas and text
response should use the same message fields so channel labels, sender, title,
time, and excerpt stay consistent. Keep samples synthetic and read-only. Escape
dynamic values with `html.escape`; leave message values as text, not markup.

For offline-safe examples, inline the required CSS, avoid JavaScript when the
view is static, and do not reference CDN assets, remote images, or external
fonts. Use a restrictive resource CSP declaration and do not declare network
domains when the view makes no network requests. Do not include real mail or
chat content, credentials, or compose/send behavior in a sample package.

This MCP Apps resource contract is separate from the declarative
`actions.canvas_contract.CanvasSpec` schema. Use the CanvasSpec contract when
the Runtime consumer accepts that schema; do not treat a CanvasSpec document as
an MCP Apps HTML resource or invent a binding API.
