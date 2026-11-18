from html import escape

from message_actions import (
    MessagePreview,
    SAMPLE_MESSAGES,
    UI_URI,
    format_message_fallback,
    message_canvas,
    open_sample_messages,
    render_message_canvas,
)


def test_canvas_and_text_fallback_render_the_same_sample_messages():
    html = message_canvas()
    fallback = open_sample_messages()

    assert isinstance(fallback, str)
    for message in SAMPLE_MESSAGES:
        assert message.title in html
        assert message.title in fallback
        assert message.sender in html
        assert message.sender in fallback
        assert message.preview in html
        assert message.preview in fallback

    assert html.count('<article class="message-card"') == 2
    assert "data-channel=\"email\"" in html
    assert "data-channel=\"chat\"" in html
    assert UI_URI == "ui://canvas-mail-chat/v1/messages.html"


def test_html_escapes_message_values_and_has_no_external_assets():
    message = MessagePreview(
        channel="Email",
        sender='Example <sender> "A"',
        title="<img src=x onerror=alert(1)>",
        timestamp="2026-11-17T09:15:00Z",
        preview="<script>unsafe()</script> & safe text",
    )

    html = render_message_canvas((message,))

    assert escape(message.sender) in html
    assert escape(message.title) in html
    assert escape(message.preview) in html
    assert "<img" not in html
    assert "<script" not in html
    assert "<iframe" not in html
    assert "<link" not in html
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "https://" not in html


def test_text_fallback_is_readable_for_text_only_clients():
    fallback = format_message_fallback(SAMPLE_MESSAGES)

    assert fallback.startswith("Example messages (offline fixture)")
    assert "Email: Quarterly planning" in fallback
    assert "Chat: Release coordination" in fallback
    assert "Preview: The draft agenda is ready for review." in fallback
    assert "Preview: The checklist is ready for the next review." in fallback
