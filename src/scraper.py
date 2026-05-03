import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


class Scraper:
    """Extracts data from web pages using CSS selectors, with multi-selector support."""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def navigate(self, url: str, verbose: bool = False):
        """Navigate to a URL."""
        if verbose:
            print(f"  [scrape] navigating to {url}", file=sys.stderr)
        self.driver.get(url)

    def _extract_single(self, selector: str) -> str | None:
        """Extract text from the first element matching the selector."""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return None

    def _extract_multi(self, selector: str) -> list[str]:
        """Extract text from ALL elements matching the selector."""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            return [el.text.strip() for el in elements if el.text.strip()]
        except Exception:
            return []

    def scrape(self, scrape_cfg: dict, verbose: bool = False) -> dict:
        """Full scrape: optionally navigate to target_url, then extract data_selectors.

        Selector values in data_selectors can be:
        - A string: extracts text from the first matching element.
        - A list of strings: extracts text from ALL elements matching each selector,
          returning a flat list of all non-empty results.
        """
        target = scrape_cfg.get("target_url")
        selectors = scrape_cfg.get("data_selectors", {})

        if not selectors:
            return {}

        if target:
            self.navigate(target, verbose=verbose)

        data = {}
        for key, sel in selectors.items():
            if verbose:
                print(f"  [scrape] extracting '{key}': {sel}", file=sys.stderr)

            if isinstance(sel, str):
                data[key] = self._extract_single(sel)
                if data[key] is None and verbose:
                    print(f"  [scrape] WARNING: element not found for '{key}' ({sel})",
                          file=sys.stderr)
            elif isinstance(sel, list):
                results: list[str] = []
                for s in sel:
                    results.extend(self._extract_multi(s))
                data[key] = results if results else None
                if not results and verbose:
                    print(f"  [scrape] WARNING: no elements found for '{key}' ({sel})",
                          file=sys.stderr)

        return data

    def scrape_full_page(self) -> str:
        body = self.driver.find_element(By.TAG_NAME, "body")
        return body.text.strip()
