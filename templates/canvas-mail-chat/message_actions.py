"""Offline MCP Apps Canvas example for consistent email and chat previews."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import Literal

from actions.mcp import resource, tool

UI_URI = "ui://canvas-mail-chat/v1/messages.html"


@dataclass(frozen=True)
class MessagePreview:
    """Normalized fields shared by email and chat message previews."""

    channel: Literal["Email", "Chat"]
    sender: str
    title: str
    timestamp: str
    preview: str


SAMPLE_MESSAGES: tuple[MessagePreview, ...] = (
    MessagePreview(
        channel="Email",
        sender="Example Sender",
        title="Quarterly planning",
        timestamp="2026-11-17T09:15:00Z",
        preview="The draft agenda is ready for review.",
    ),
    MessagePreview(
        channel="Chat",
        sender="Example Participant",
        title="Release coordination",
        timestamp="2026-11-17T09:42:00Z",
        preview="The checklist is ready for the next review.",
    ),
)


def render_message_canvas(
    messages: Sequence[MessagePreview] = SAMPLE_MESSAGES,
) -> str:
    """Render normalized message values as a self-contained Canvas resource."""
    cards = "\n".join(
        f"""
        <article class="message-card" data-channel="{escape(message.channel.lower(), quote=True)}">
          <p class="message-card__channel">{escape(message.channel)}</p>
          <h2>{escape(message.title)}</h2>
          <dl class="message-card__details">
            <div><dt>From</dt><dd>{escape(message.sender)}</dd></div>
            <div><dt>Time</dt><dd><time datetime="{escape(message.timestamp, quote=True)}">{escape(message.timestamp)}</time></dd></div>
          </dl>
          <p class="message-card__preview">{escape(message.preview)}</p>
        </article>
        """
        for message in messages
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Example messages</title>
    <style>
      :root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #182230; background: #f4f7fb; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; }}
      main {{ width: min(100% - 2rem, 48rem); margin: 0 auto; padding: 2rem 0; }}
      h1 {{ margin: 0; font-size: clamp(1.6rem, 5vw, 2.2rem); }}
      .intro {{ margin: .5rem 0 1.25rem; color: #425466; }}
      .message-list {{ display: grid; gap: 1rem; }}
      .message-card {{ padding: 1rem 1.1rem; border: 1px solid #d5dde7; border-radius: .65rem; background: #fff; box-shadow: 0 .3rem 1rem #1822300d; }}
      .message-card__channel {{ margin: 0 0 .35rem; color: #165d76; font-size: .75rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }}
      .message-card h2 {{ margin: 0; font-size: 1.1rem; }}
      .message-card__details {{ display: flex; flex-wrap: wrap; gap: .35rem 1.5rem; margin: .65rem 0; color: #425466; font-size: .875rem; }}
      .message-card__details div {{ display: flex; gap: .35rem; }}
      .message-card__details dt {{ font-weight: 650; }}
      .message-card__details dd {{ margin: 0; overflow-wrap: anywhere; }}
      .message-card__preview {{ margin: 0; line-height: 1.55; overflow-wrap: anywhere; }}
      @media (max-width: 36rem) {{ main {{ padding: 1rem 0; }} .message-card {{ border-radius: .45rem; }} }}
    </style>
  </head>
  <body>
    <main aria-labelledby="messages-title">
      <h1 id="messages-title">Example messages</h1>
      <p class="intro">Email and chat use the same readable message layout.</p>
      <section class="message-list" aria-label="Messages">
        {cards}
      </section>
    </main>
  </body>
</html>
"""


def format_message_fallback(
    messages: Sequence[MessagePreview] = SAMPLE_MESSAGES,
) -> str:
    """Format the same messages for clients that show MCP text results."""
    entries = [
        "\n".join(
            (
                f"{message.channel}: {message.title}",
                f"From: {message.sender}",
                f"Time: {message.timestamp}",
                f"Preview: {message.preview}",
            )
        )
        for message in messages
    ]
    return "Example messages (offline fixture)\n\n" + "\n\n".join(entries)


@resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {}}},
)
def message_canvas() -> str:
    """Provide the self-contained HTML view for the sample messages."""
    return render_message_canvas()


@tool(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
    meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}},
)
def open_sample_messages() -> str:
    """Show sample mail and chat in Canvas or return a text-first fallback."""
    return format_message_fallback()
