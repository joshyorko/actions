"""
Type definitions for work items.

Based on robocorp-workitems (Apache 2.0 License).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# JSON-compatible types
JSONType = str | int | float | bool | None | dict[str, Any] | list[Any]

# Week in seconds
TTL_WEEK_SECONDS = 604_800

# Path type for file operations
PathType = Path | str


class State(str, Enum):
    """Work item processing states."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "COMPLETED"
    FAILED = "FAILED"
    # Alias for robocorp compatibility
    COMPLETED = "COMPLETED"

    @classmethod
    def _missing_(cls, value):
        """Handle COMPLETED -> DONE mapping."""
        if isinstance(value, str) and value.upper() in {"DONE", "COMPLETED"}:
            return cls.DONE
        return None


class ExceptionType(str, Enum):
    """Types of exceptions that can occur during work item processing."""

    # Business exception - expected failure that should not be retried
    BUSINESS = "BUSINESS"
    # Application exception - unexpected failure that may be retried
    APPLICATION = "APPLICATION"


@dataclass
class Address:
    """Email address with optional display name."""

    address: str
    name: str = ""

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address


@dataclass
class Email:
    """
    Parsed email message from work item attachment.

    Provides structured access to email fields commonly used
    in email-triggered automation workflows.
    """

    from_: Address | None = None
    to: list[Address] = field(default_factory=list)
    cc: list[Address] = field(default_factory=list)
    bcc: list[Address] = field(default_factory=list)
    subject: str | None = None
    date: datetime | None = None
    text: str | None = None
    html: str | None = None
    reply_to: Address | None = None
    message_id: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def sender(self) -> Address | None:
        return self.from_

    @property
    def recipients(self) -> list[Address]:
        return self.to

    @property
    def body(self) -> str | None:
        return self.text

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Email":
        def address(field: str, optional: bool = False):
            raw = value.get(field) if optional else value[field]
            if raw is None:
                return None
            if not isinstance(raw, dict):
                raise TypeError(f"Expected '{field}' as dict")
            return Address(name=raw.get("name", ""), address=raw["address"])

        def addresses(field: str):
            raw = value[field]
            if not isinstance(raw, list):
                raise TypeError(f"Expected '{field}' as list")
            return [Address(name=item.get("name", ""), address=item["address"]) for item in raw]

        reply_key = "replyTo" if "replyTo" in value else "reply_to"
        return cls(
            from_=address("from"),
            to=addresses("to"),
            cc=addresses("cc"),
            bcc=addresses("bcc"),
            subject=value["subject"],
            date=datetime.fromisoformat(value["date"].replace("Z", "+00:00")),
            reply_to=address(reply_key, optional=True),
            message_id=value.get("messageId", value.get("message_id")),
            text=value.get("text"),
        )

    @classmethod
    def from_bytes(cls, content: bytes) -> "Email":
        """
        Parse email from raw bytes content.

        Args:
            content: Raw email bytes (RFC 822 format).

        Returns:
            Parsed Email object.
        """
        import email
        from email.header import decode_header
        from email.utils import parseaddr, parsedate_to_datetime

        errors = []
        msg = email.message_from_bytes(content)

        def decode_str(value: str | None) -> str | None:
            if not value:
                return None
            try:
                decoded_parts = decode_header(value)
                result = []
                for part, charset in decoded_parts:
                    if isinstance(part, bytes):
                        result.append(part.decode(charset or "utf-8", errors="replace"))
                    else:
                        result.append(part)
                return "".join(result)
            except Exception as e:
                errors.append(f"Header decode error: {e}")
                return value

        def parse_address(value: str | None) -> Address | None:
            if not value:
                return None
            name, addr = parseaddr(value)
            if addr:
                return Address(address=addr, name=decode_str(name) if name else None)
            return None

        def parse_addresses(value: str | None) -> list[Address]:
            if not value:
                return []
            addresses = []
            for part in value.split(","):
                addr = parse_address(part.strip())
                if addr:
                    addresses.append(addr)
            return addresses

        def get_body(msg) -> tuple:
            body = None
            html = None
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" and body is None:
                        try:
                            body = part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="replace"
                            )
                        except Exception as e:
                            errors.append(f"Body decode error: {e}")
                    elif content_type == "text/html" and html is None:
                        try:
                            html = part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="replace"
                            )
                        except Exception as e:
                            errors.append(f"HTML decode error: {e}")
            else:
                content_type = msg.get_content_type()
                try:
                    payload = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", errors="replace"
                    )
                    if content_type == "text/html":
                        html = payload
                    else:
                        body = payload
                except Exception as e:
                    errors.append(f"Payload decode error: {e}")
            return body, html

        date = None
        date_str = msg.get("Date")
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception as e:
                errors.append(f"Date parse error: {e}")

        body, html = get_body(msg)

        return cls(
            from_=parse_address(msg.get("From")),
            to=parse_addresses(msg.get("To")),
            cc=parse_addresses(msg.get("Cc")),
            bcc=parse_addresses(msg.get("Bcc")),
            subject=decode_str(msg.get("Subject")),
            date=date,
            text=body,
            html=html,
            reply_to=parse_address(msg.get("Reply-To")),
            message_id=msg.get("Message-ID"),
            errors=errors,
        )
