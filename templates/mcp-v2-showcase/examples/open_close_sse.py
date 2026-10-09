"""Open and close the stateless Streamable HTTP GET/SSE channel."""

from __future__ import annotations

import argparse
import http.client
from urllib.parse import urlsplit


def open_channel(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or not parsed.hostname:
        raise ValueError("this local lifecycle example requires an http:// URL")

    connection = http.client.HTTPConnection(
        parsed.hostname, parsed.port or 80, timeout=5
    )
    try:
        connection.request(
            "GET",
            parsed.path or "/mcp",
            headers={"Accept": "text/event-stream", "Connection": "keep-alive"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"SSE open returned HTTP {response.status}.")
        if response.getheader("Content-Type", "").split(";", 1)[0] != (
            "text/event-stream"
        ):
            raise RuntimeError("SSE open did not return text/event-stream.")
        print("The stateless GET/SSE channel opened successfully.")
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080/mcp")
    args = parser.parse_args()
    try:
        open_channel(args.base_url)
    except ValueError as error:
        parser.error(str(error))
    print("Closed the channel; no progress event was requested or expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
