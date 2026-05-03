from pathlib import Path

import pytest

from src.scraper import Scraper
from src.lab_finder import LabFinder


BOOKS_HOMEPAGE = "https://books.toscrape.com/"
OUTPUT_FILE = Path("last-lab-content.txt")


@pytest.mark.integration
class TestLabScrape:
    def test_find_last_lab_and_scrape_content(self, driver):
        scraper = Scraper(driver)
        scraper.navigate(BOOKS_HOMEPAGE)

        finder = LabFinder(driver)
        clicked = finder.click_last_lab(".side_categories a[href]")

        assert clicked is True, "Should have clicked last category link"

        content = scraper.scrape_full_page()
        assert len(content) > 0

        OUTPUT_FILE.write_text(content, encoding="utf-8")
        assert OUTPUT_FILE.exists()
        assert OUTPUT_FILE.stat().st_size > 0

    def test_find_last_lab_no_matches_returns_false(self, driver):
        scraper = Scraper(driver)
        scraper.navigate(BOOKS_HOMEPAGE)

        finder = LabFinder(driver)
        clicked = finder.click_last_lab("#this-selector-does-not-exist-xyz")

        assert clicked is False
