import shutil
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def _find_chrome_binary() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    puppeteer_bin = Path.home() / "chromium"
    if puppeteer_bin.exists():
        candidates = sorted(puppeteer_bin.glob("**/chrome"))
        candidates = [c for c in candidates if "chrome" in c.parent.name.lower() and c.is_file()]
        if candidates:
            return str(candidates[0])
    return None


def _find_chromedriver() -> str | None:
    path = shutil.which("chromedriver")
    if path:
        return path
    puppeteer_bin = Path.home() / "chromium"
    if puppeteer_bin.exists():
        candidates = sorted(puppeteer_bin.glob("**/chromedriver"))
        candidates = [c for c in candidates if c.is_file()]
        if candidates:
            return str(candidates[0])
    return None


def create_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    binary = _find_chrome_binary()
    if binary:
        opts.binary_location = binary

    driver_path = _find_chromedriver()
    if driver_path:
        service = Service(driver_path)
    else:
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(30)
    return driver
