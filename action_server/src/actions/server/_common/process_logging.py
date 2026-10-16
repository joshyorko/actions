"""Redaction helpers for subprocess diagnostics."""

from __future__ import annotations

from typing import Sequence


def redact_sensitive_arguments(arguments: Sequence[str]) -> list[str]:
    """Redact API-key switches, including the CLI's accepted abbreviations."""
    redacted: list[str] = []
    redact_next = False
    for argument in arguments:
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
        elif (
            argument.startswith("--")
            and len(argument.partition("=")[0]) > 2
            and "--api-key".startswith(argument.partition("=")[0])
        ):
            option, separator, _ = argument.partition("=")
            if separator:
                redacted.append(f"{option}=<redacted>")
            else:
                redacted.append(option)
                redact_next = True
        else:
            redacted.append(argument)
    return redacted
