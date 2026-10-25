"""Check retained Knowledge page artifacts; this is not an execution driver.

The installed lifecycle driver must supply separately authorized pages before and
after restart. Passing this checker proves only page completeness/provenance and
byte stability, not installed origin, RCC execution, grants or Task publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IDENTITY = ("version", "revision", "ingestionHandle", "corpusDigest", "query", "total")
FIELDS = set(IDENTITY) | {"offset", "limit", "hits"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def validate_pages(pages: list[bytes], expected_hits: list[dict], *, max_bytes: int):
    """Validate complete ordered fixture results and return nonsecret hashes.

    Expected hits come from the owned fixture, independently of returned pages.
    No result grants authority, creates an export, or changes a provider.
    """
    if (
        not pages
        or not isinstance(max_bytes, int)
        or isinstance(max_bytes, bool)
        or max_bytes < 1
    ):
        raise ValueError("nonempty bounded page inventory required")
    if sum(len(raw) for raw in pages) > max_bytes:
        raise ValueError("page inventory exceeds byte budget")
    identity = None
    hits = []
    seen = set()
    hashes = []
    for index, raw in enumerate(pages):
        page = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(page, dict) or set(page) != FIELDS:
            raise ValueError("unexpected search page shape")
        if page["version"] != "actions.knowledge-search/v1":
            raise ValueError("unsupported search page version")
        if any(
            not isinstance(page[key], int) or isinstance(page[key], bool)
            for key in ("offset", "limit", "total")
        ):
            raise ValueError("integer pagination required")
        if page["offset"] != len(hits) or page["limit"] < 1 or page["total"] < 0:
            raise ValueError("noncontiguous pagination")
        current = {key: page[key] for key in IDENTITY}
        if identity is not None and current != identity:
            raise ValueError("search provenance changed between pages")
        identity = current
        batch = page["hits"]
        if not isinstance(batch, list) or len(batch) != min(
            page["limit"], page["total"] - page["offset"]
        ):
            raise ValueError("incomplete or overfull search page")
        if index and not batch:
            raise ValueError("redundant empty page")
        for document in batch:
            if not isinstance(document, dict) or not isinstance(
                document.get("id"), str
            ):
                raise ValueError("document identity required")
            if document["id"] in seen:
                raise ValueError("duplicate document across pages")
            seen.add(document["id"])
        hits.extend(batch)
        hashes.append(hashlib.sha256(raw).hexdigest())
    if len(hits) != identity["total"] or hits != expected_hits:
        raise ValueError("complete fixture result differs")
    return {"documents": len(hits), "pages": len(pages), "sha256": hashes}


def validate_restart(before, after, expected_hits, *, max_bytes):
    first = validate_pages(before, expected_hits, max_bytes=max_bytes)
    second = validate_pages(after, expected_hits, max_bytes=max_bytes)
    if first != second:
        raise ValueError("downloaded page bytes changed after restart")
    return first


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, nargs="+", required=True)
    parser.add_argument("--after", type=Path, nargs="+", required=True)
    parser.add_argument("--expected-hits", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, required=True)
    args = parser.parse_args()
    # Refuse oversized files before reading their contents.
    for group in (args.before, args.after):
        if sum(path.stat().st_size for path in group) > args.max_bytes:
            parser.error("page inventory exceeds byte budget")
    result = validate_restart(
        [path.read_bytes() for path in args.before],
        [path.read_bytes() for path in args.after],
        json.loads(args.expected_hits.read_bytes(), object_pairs_hook=_unique_object),
        max_bytes=args.max_bytes,
    )
    print(
        json.dumps({"page_artifacts": "PASS", "execution": "NOT_QUALIFIED", **result})
    )


if __name__ == "__main__":
    main()
