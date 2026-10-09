from showcase_actions import (
    catalog_overview,
    explain_demo_item,
    item_resource,
    lookup_demo_item,
    search_demo_catalog,
)


def test_search_returns_a_bounded_structured_table():
    response = search_demo_catalog("guide", limit=20)

    assert response.error is None
    assert response.result is not None
    assert response.result.columns == ["item_id", "title", "category", "summary"]
    assert response.result.rows == [
        [
            "alpha",
            "Alpha field guide",
            "guide",
            "A short guide to the sample catalog.",
        ]
    ]


def test_lookup_has_fixed_safe_error_without_reflecting_the_unknown_id():
    response = lookup_demo_item("private-marker-9f6a")

    assert response.result is None
    assert response.error == "No demo item matches this ID."
    assert "private-marker-9f6a" not in str(response)


def test_catalog_resource_template_and_prompt_are_local_and_deterministic():
    assert "alpha field guide" in catalog_overview()
    assert item_resource("bravo") == (
        "Bravo checklist: A concise checklist for trying the demo."
    )
    assert item_resource("unknown-marker") == "No demo item matches this ID."
    assert explain_demo_item("charlie") == (
        "Explain Charlie reference using this summary: "
        "A small reference entry with no external data."
    )


def test_empty_search_returns_fixed_safe_error():
    response = search_demo_catalog("  ")

    assert response.error == "Search text must not be empty."
    assert response.result is None
