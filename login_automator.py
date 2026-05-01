#!/usr/bin/env python3

import argparse
import json
import sys
import time
from pathlib import Path

from src.config import load_config, validate_site
from src.classifier import classify_error
from src.driver import create_driver
from src.login import do_login, load_cookies, apply_cookies, save_cookies
from src.scraper import Scraper
from src.reporter import LoginResult, Reporter

MAX_RETRIES = 3
RETRY_DELAY = 5
DEFAULT_CONFIG = "config/sites.json"


def _build_result(name: str, status: str, data: dict | None = None,
                  error: str | None = None) -> dict:
    result: dict = {"site": name, "status": status}
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return result


def _run_scrape_only(driver, site: dict, cookies_file: Path, verbose: bool,
                     name: str) -> dict:
    cookies = load_cookies(cookies_file)
    scrape_cfg = site.get("scrape", {})
    base_url = scrape_cfg.get("target_url") or site["url"]
    if verbose:
        print(f"  [cookies] loading {len(cookies)} cookie(s) from {cookies_file}", file=sys.stderr)
    apply_cookies(driver, cookies, base_url)
    scraper = Scraper(driver)
    data = scraper.scrape(scrape_cfg, verbose)
    return _build_result(name, "success", data)


def process_site(site: dict, verbose: bool, scrape_only: bool = False,
                 cookies_file: Path | None = None,
                 save_cookies_path: Path | None = None) -> dict:
    name = site["name"]
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        driver = None
        try:
            driver = create_driver()

            if scrape_only and cookies_file:
                return _run_scrape_only(driver, site, cookies_file, verbose, name)

            ok, msg = do_login(driver, site, verbose)

            if ok:
                if save_cookies_path:
                    if verbose:
                        print(f"  [cookies] saving to {save_cookies_path}", file=sys.stderr)
                    save_cookies(driver, save_cookies_path)

                scraper = Scraper(driver)
                scrape_cfg = site.get("scrape", {})
                data = scraper.scrape(scrape_cfg, verbose)
                return _build_result(name, "success", data)
            else:
                return _build_result(name, "failed", error=msg)

        except Exception as exc:
            cat = classify_error(exc)
            last_error = str(exc)
            if cat == "client":
                if verbose:
                    print(f"  CLIENT ERROR: {exc}", file=sys.stderr)
                return _build_result(name, "failed", error=last_error)

            if verbose:
                print(f"  [attempt {attempt}/{MAX_RETRIES}] NETWORK ERROR: {exc}",
                      file=sys.stderr)

            if attempt < MAX_RETRIES:
                if verbose:
                    print(f"  retrying in {RETRY_DELAY}s...", file=sys.stderr)
                time.sleep(RETRY_DELAY)

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    return _build_result(name, "failed", error=last_error or "All retries exhausted")


def _validate_args(args):
    """Validate CLI argument combinations and exit with error on invalid input."""
    if args.scrape_only and not args.cookies_file:
        print(json.dumps({"error": "--scrape-only requires --cookies-file"}),
              file=sys.stderr)
        sys.exit(1)

    if args.scrape_only and args.save_cookies:
        print(json.dumps({"error": "--save-cookies requires a login; cannot be used with --scrape-only"}),
              file=sys.stderr)
        sys.exit(1)

    if args.cookies_file and not args.cookies_file.exists():
        print(json.dumps({"error": f"Cookies file not found: {args.cookies_file}"}),
              file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Automated website login + scraping")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"Path to config JSON (default: {DEFAULT_CONFIG})")
    parser.add_argument("--site", help="Only process the named site")
    parser.add_argument("--no-verbose", action="store_true",
                        help="Suppress debug output")
    parser.add_argument("--scrape-only", action="store_true",
                        help="Skip login; reuse session via --cookies-file")
    parser.add_argument("--cookies-file", type=Path,
                        help="Path to JSON cookies file (required with --scrape-only)")
    parser.add_argument("--save-cookies", type=Path,
                        help="Save session cookies to a JSON file after successful login")
    parser.add_argument("--report-file", type=Path,
                        help="Append human-readable report to a file (default: stderr)")
    args = parser.parse_args()
    _validate_args(args)

    verbose = not args.no_verbose
    config_path = Path(args.config)

    if not config_path.exists():
        print(json.dumps({"error": f"Config not found: {config_path}"}), file=sys.stderr)
        sys.exit(1)

    try:
        config = load_config(config_path)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"error": f"Config read error: {e}"}), file=sys.stderr)
        sys.exit(1)

    sites = config.get("sites", [])
    if not sites:
        print(json.dumps({"error": "No sites defined in config"}), file=sys.stderr)
        sys.exit(1)

    for i, s in enumerate(sites):
        try:
            validate_site(s, i)
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)

    if args.site:
        sites = [s for s in sites if s["name"] == args.site]
        if not sites:
            print(json.dumps({"error": f"Site '{args.site}' not found"}), file=sys.stderr)
            sys.exit(1)

    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)

    overall = "success"
    for site in sites:
        if verbose:
            print(f"=== Processing: {site['name']} ===", file=sys.stderr)
        result = process_site(site, verbose,
                              scrape_only=args.scrape_only,
                              cookies_file=args.cookies_file,
                              save_cookies_path=args.save_cookies)
        print(json.dumps(result))

        entry = LoginResult(
            site=result["site"],
            status=result["status"],
            timestamp=result["timestamp"],
            data=result.get("data", {}),
            error=result.get("error"),
        )
        Reporter.write(entry, dest=args.report_file)

        if result["status"] != "success":
            overall = "failed"
        if verbose:
            print(f"--- Result: {result['status']} ---\n", file=sys.stderr)

    sys.exit(0 if overall == "success" else 1)


if __name__ == "__main__":
    main()