# Canvas mail and chat example

This standalone Action package renders synthetic email and chat previews in one
consistent MCP Apps Canvas view. Both the HTML resource and the tool's plain
text response use the same message records. MCP Apps hosts can open the Canvas;
T3 and other text-first clients still receive a readable result from the same
tool call.

The example uses the public `actions.mcp` decorators and the Action Server's
`text/html;profile=mcp-app` resource contract. Its sample records are fixed and
synthetic. The resource is generated locally with inline CSS, has no JavaScript
or external assets, and escapes message values before inserting them into HTML.
The read-only tool does not connect to mail or chat services, send messages, or
require credentials.

Run the package with an installed Action Server:

```bash
action-server start
```

The MCP tool is `open_sample_messages`. Its text response is the fallback for
clients that do not display the Canvas resource. Replace `SAMPLE_MESSAGES` with
your own read-only data source when adapting the example, and keep the HTML and
text views on the same normalized message fields.

The Canvas uses a shared shape for both channels:

| Field | Email | Chat |
| --- | --- | --- |
| Channel | Email | Chat |
| Sender | From name | Participant name |
| Title | Subject | Conversation title |
| Time | Message time | Message time |
| Preview | Body excerpt | Message excerpt |

The package is a source example under `templates/`; it is not part of the
generated `action-server new` template bundle.
