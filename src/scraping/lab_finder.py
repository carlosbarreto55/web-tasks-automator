import sys

from selenium import webdriver
from selenium.webdriver.common.by import By


_LOCATOR_MAP = {
    "css": By.CSS_SELECTOR,
    "xpath": By.XPATH,
}


class LabFinder:
    """Finds and interacts with lab links on a course page."""

    def __init__(self, driver: webdriver.Chrome, locator_type: str = "css"):
        self.driver = driver
        if locator_type not in _LOCATOR_MAP:
            raise ValueError(f"Invalid locator_type '{locator_type}'; must be one of {list(_LOCATOR_MAP.keys())}")
        self._by = _LOCATOR_MAP[locator_type]

    def find_lab_links(self, selector: str) -> list:
        return self.driver.find_elements(self._by, selector)

    def get_last_lab(self, selector: str):
        links = self.find_lab_links(selector)
        if not links:
            return None
        return links[-1]

    def click_last_lab(self, selector: str, verbose: bool = False) -> bool:
        last = self.get_last_lab(selector)
        if last is None:
            if verbose:
                print(f"  [labs] no lab links found for selector '{selector}'",
                      file=sys.stderr)
            return False
        if verbose:
            print(f"  [labs] clicking last lab: {last.text.strip()[:80]}",
                  file=sys.stderr)
        last.click()
        return True

    def get_last_lab_url(self, selector: str, verbose: bool = False) -> str | None:
        last = self.get_last_lab(selector)
        if last is None:
            if verbose:
                print(f"  [labs] no lab links found for selector '{selector}'",
                      file=sys.stderr)
            return None
        url = last.get_attribute("href")
        if verbose:
            print(f"  [labs] last lab URL: {url}", file=sys.stderr)
        return url
