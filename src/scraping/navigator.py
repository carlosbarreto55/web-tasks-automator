import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

DEFAULT_WAIT_TIMEOUT = 10


class Navigator:
    """Clicks through a sequence of elements to navigate a site after login."""

    def __init__(self, driver: webdriver.Chrome, steps: list[dict]):
        self.driver = driver
        self.steps = steps

    def _click(self, selector: str, verbose: bool):
        if verbose:
            print(f"  [navigate] clicking: {selector}", file=sys.stderr)
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()

    def _navigate_to(self, url: str, verbose: bool):
        if verbose:
            print(f"  [navigate] navigating to: {url}", file=sys.stderr)
        self.driver.get(url)

    def _wait_for_element(self, selector: str, timeout: int, verbose: bool):
        if verbose:
            print(f"  [navigate] waiting for: {selector} (timeout={timeout}s)",
                  file=sys.stderr)
        wait = WebDriverWait(self.driver, timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

    def run(self, verbose: bool = False):
        """Execute all navigation steps in order."""
        for i, step in enumerate(self.steps):
            if verbose:
                print(f"  [navigate] step {i + 1}/{len(self.steps)}", file=sys.stderr)

            if "url" in step:
                self._navigate_to(step["url"], verbose)
            elif "click" in step:
                self._click(step["click"], verbose)

                wait_for = step.get("wait_for")
                if wait_for:
                    timeout = step.get("wait_timeout", DEFAULT_WAIT_TIMEOUT)
                    self._wait_for_element(wait_for, timeout, verbose)

                wait_after = step.get("wait_after")
                if wait_after:
                    if verbose:
                        print(f"  [navigate] sleeping {wait_after}s", file=sys.stderr)
                    time.sleep(wait_after)
            else:
                raise ValueError(f"Navigate step {i + 1} must contain 'click' or 'url'")
