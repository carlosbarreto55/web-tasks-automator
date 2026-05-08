from pathlib import Path

import pytest

from src.scraping.navigator import Navigator
from src.scraping.scraper import Scraper


_OUTPUT = Path(__file__).parent / "last-navtest-output.txt"
BOOKS_HOMEPAGE = "https://books.toscrape.com/"


def _write_output(test_name: str, data: dict):
    lines = []
    lines.append("=" * 70)
    lines.append(f"Test: {test_name}")
    lines.append("=" * 70)
    for key, value in data.items():
        value_str = "None" if value is None else str(value)
        lines.append(f"{key}: {value_str}")
    lines.append("")
    with open(_OUTPUT, "a") as f:
        f.write("\n".join(lines) + "\n")


@pytest.mark.integration
class TestScrapeWithoutLogin:
    def test_scrape_page_title_and_books(self, driver):
        scraper = Scraper(driver)
        scraper.navigate(BOOKS_HOMEPAGE)

        cfg = {
            "data_selectors": {
                "page_title": "h1",
                "first_book_title": ".product_pod h3 a",
            }
        }
        data = scraper.scrape(cfg)

        assert data["page_title"] is not None
        assert "all products" in data["page_title"].lower()
        assert data["first_book_title"] is not None
        assert len(data["first_book_title"]) > 0

        _write_output("TestScrapeWithoutLogin.test_scrape_page_title_and_books", data)

    def test_scrape_missing_selector_returns_none(self, driver):
        scraper = Scraper(driver)
        scraper.navigate(BOOKS_HOMEPAGE)

        cfg = {
            "data_selectors": {
                "exists": "h1",
                "missing": "#this-does-not-exist-xyz",
            }
        }
        data = scraper.scrape(cfg)

        assert data["exists"] is not None
        assert data["missing"] is None

        _write_output("TestScrapeWithoutLogin.test_scrape_missing_selector_returns_none", data)


@pytest.mark.integration
class TestNavigateAndScrape:
    def test_click_category_link_then_scrape(self, driver):
        scraper = Scraper(driver)
        scraper.navigate(BOOKS_HOMEPAGE)

        steps = [
            {"click": ".side_categories a[href*='travel']", "wait_for": "h1"},
        ]
        nav = Navigator(driver, steps)
        nav.run()

        cfg = {"data_selectors": {"heading": "h1"}}
        data = scraper.scrape(cfg)

        assert data["heading"] is not None
        assert "travel" in data["heading"].lower()

        _write_output("TestNavigateAndScrape.test_click_category_link_then_scrape", data)

    def test_click_category_with_wait_after(self, driver):
        scraper = Scraper(driver)
        scraper.navigate(BOOKS_HOMEPAGE)

        steps = [
            {"click": ".side_categories a[href*='travel']", "wait_after": 2},
        ]
        nav = Navigator(driver, steps)
        nav.run()

        cfg = {"data_selectors": {"heading": "h1"}}
        data = scraper.scrape(cfg)

        assert data["heading"] is not None
        assert "travel" in data["heading"].lower()

        _write_output("TestNavigateAndScrape.test_click_category_with_wait_after", data)

    def test_url_step_navigates_directly(self, driver):
        scraper = Scraper(driver)

        steps = [
            {"url": BOOKS_HOMEPAGE},
        ]
        nav = Navigator(driver, steps)
        nav.run()

        cfg = {"data_selectors": {"heading": "h1"}}
        data = scraper.scrape(cfg)

        assert data["heading"] is not None
        assert "all products" in data["heading"].lower()

        _write_output("TestNavigateAndScrape.test_url_step_navigates_directly", data)
