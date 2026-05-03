import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def do_login(driver: webdriver.Chrome, site: dict, verbose: bool) -> tuple[bool, str | None]:
    url = site["url"]
    sel = site["selectors"]
    creds = site["credentials"]

    if verbose:
        print(f"  [login] navigating to {url}", file=sys.stderr)
    driver.get(url)

    if verbose:
        print(f"  [login] filling username: {sel['username_input']}", file=sys.stderr)
    driver.find_element(By.CSS_SELECTOR, sel["username_input"]).send_keys(creds["username"])

    if verbose:
        print(f"  [login] filling password: {sel['password_input']}", file=sys.stderr)
    driver.find_element(By.CSS_SELECTOR, sel["password_input"]).send_keys(creds["password"])

    if verbose:
        print(f"  [login] clicking submit: {sel['submit_button']}", file=sys.stderr)
    driver.find_element(By.CSS_SELECTOR, sel["submit_button"]).click()

    wait = WebDriverWait(driver, 15)
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, sel["success_indicator"])))
        return True, None
    except TimeoutException:
        pass

    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, sel["failure_indicator"])))
        try:
            msg = driver.find_element(By.CSS_SELECTOR, sel["failure_indicator"]).text.strip()
        except Exception:
            msg = "Login failed (error indicator found)"
        return False, msg
    except TimeoutException:
        pass

    return False, "Could not determine login outcome (no indicator found within timeout)"


def load_cookies(path: Path) -> list[dict]:
    """Load browser cookies from a JSON file."""
    with open(path) as f:
        return json.load(f)


def apply_cookies(driver: webdriver.Chrome, cookies: list[dict], url: str):
    """Apply cookies to the driver for the given URL's domain."""
    parsed = urlparse(url)
    driver.get(f"{parsed.scheme}://{parsed.netloc}/")
    for cookie in cookies:
        driver.add_cookie(cookie)


def save_cookies(driver: webdriver.Chrome, path: Path):
    """Save current browser cookies to a JSON file."""
    cookies = driver.get_cookies()
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)
