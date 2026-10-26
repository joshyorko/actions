"""Synthetic checker tests, never installed Knowledge acceptance evidence."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "lane_b_checker",
    Path(__file__).parents[2] / "scripts" / "qualify_lane_b_installed_knowledge.py",
)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

HITS = [{"id": "one", "text": "owned first"}, {"id": "two", "text": "owned second"}]


def page(offset=0, **changes):
    value = dict(
        version="actions.knowledge-search/v1",
        revision={"revision_id": "fixture-revision"},
        ingestionHandle="fixture-handle",
        corpusDigest="fixture-digest",
        query="owned",
        offset=offset,
        limit=1,
        total=2,
        hits=HITS[offset : offset + 1],
    )
    value.update(changes)
    return json.dumps(value).encode()


def test_complete_pages_retain_exact_bytes_across_restart():
    pages = [page(), page(1)]
    result = checker.validate_restart(pages, pages, HITS, max_bytes=4096)
    assert result["documents"] == 2
    assert result["pages"] == 2


@pytest.mark.parametrize("field", checker.IDENTITY)
def test_rejects_mixed_provenance(field):
    with pytest.raises(ValueError):
        checker.validate_pages(
            [page(), page(1, **{field: "changed"})], HITS, max_bytes=4096
        )


@pytest.mark.parametrize(
    "pages",
    [
        [],
        [page()],
        [page(1), page()],
        [page(), page(1, hits=[HITS[0]])],
        [page(hits=[])],
        [page(offset=True)],
        [page(), page(1), page(2)],
        [page()[:-1] + b', "total": 2}'],
    ],
)
def test_rejects_incomplete_ambiguous_or_duplicate_pages(pages):
    with pytest.raises(ValueError):
        checker.validate_pages(pages, HITS, max_bytes=4096)


def test_independent_fixture_and_byte_budget_are_required():
    with pytest.raises(ValueError):
        checker.validate_pages([page(), page(1)], [], max_bytes=4096)
    with pytest.raises(ValueError):
        checker.validate_pages([page(), page(1)], HITS, max_bytes=1)


def test_semantic_equality_does_not_hide_changed_download_bytes():
    with pytest.raises(ValueError, match="bytes changed"):
        checker.validate_restart(
            [page(), page(1)], [page() + b"\n", page(1)], HITS, max_bytes=4096
        )


def test_empty_search_is_one_complete_page():
    result = checker.validate_pages([page(total=0, hits=[])], [], max_bytes=4096)
    assert result["documents"] == 0
