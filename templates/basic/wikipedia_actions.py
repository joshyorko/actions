"""A simple AI Action template for retrieving a Wikipedia article summary."""

import os

from actions import Response, action
from robocorp import browser

HEADLESS_BROWSER = not os.getenv("HEADLESS_BROWSER")


@action
def get_wikipedia_article_summary(article_url: str) -> Response[str]:
    """Retrieve the first paragraph of a Wikipedia article."""
    browser.configure(browser_engine="chromium", headless=HEADLESS_BROWSER)
    page = browser.goto(article_url)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")
    paragraphs = page.query_selector_all(".mw-content-ltr>p:not(.mw-empty-elt)")
    summary = paragraphs[0].inner_text()
    print(summary)
    return Response(result=summary)
