import os
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_E2E") != "1",
    reason="需要显式开启浏览器 E2E",
)
def test_chat_input_is_ready():
    playwright_api = pytest.importorskip("playwright.sync_api")

    report_dir = (
        Path(__file__).resolve().parents[2] / "reports" / "e2e"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)

        try:
            page = browser.new_page()
            page.goto(
                "http://127.0.0.1:8502",
                wait_until="domcontentloaded",
            )

            chat_input = page.get_by_placeholder(
                "any task?",
                exact=True,
            )

            playwright_api.expect(chat_input).to_be_visible(
                timeout=30_000
            )
            playwright_api.expect(chat_input).to_be_editable()

            page.screenshot(
                path=str(report_dir / "page-ready.png"),
                full_page=True,
            )
        finally:
            browser.close()