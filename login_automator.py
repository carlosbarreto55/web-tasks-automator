#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
from pathlib import Path

from src.config.config import load_config, validate_site
from src.login.classifier import classify_error
from src.login.driver import create_driver
from src.login.login import do_login, load_cookies, apply_cookies, save_cookies
from src.scraping.navigator import Navigator
from src.scraping.scraper import Scraper
from src.scraping.lab_finder import LabFinder
from src.reporter import LoginResult, Reporter
from src.ai.ai_client import OpenAIClient, OllamaClient
from src.ai.solver import LabSolver
from src.config.notifications_config import load_telegram_config, create_notifier

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


def _process_labs(driver, site: dict, verbose: bool,
                  notifier=None):
    labs_cfg = site.get("labs")
    if not labs_cfg:
        return
    selector = labs_cfg.get("lab_link_selector")
    if not selector:
        if verbose:
            print("  [labs] no lab_link_selector configured, skipping",
                  file=sys.stderr)
        return

    locator_type = labs_cfg.get("locator_type", "css")
    finder = LabFinder(driver, locator_type=locator_type)

    lab_url = finder.get_last_lab_url(selector, verbose=verbose)
    if lab_url is None:
        if verbose:
            print("  [labs] no lab URL found, skipping",
                  file=sys.stderr)
        return

    scraper = Scraper(driver)
    scraper.navigate(lab_url, verbose=verbose)

    content = scraper.scrape_full_page()
    output_file = Path(labs_cfg.get("output_file", "last-lab-content.txt"))
    output_file.write_text(content, encoding="utf-8")
    if verbose:
        print(f"  [labs] saved {len(content)} chars to {output_file}",
              file=sys.stderr)

    if notifier:
        try:
            notifier.notify_lab_saved(site["name"], output_file,
                                      len(content), verbose=verbose)
        except Exception as exc:
            if verbose:
                print(f"  [notify] error: {exc}", file=sys.stderr)


def _process_solve(site: dict, verbose: bool, notifier=None):
    labs_cfg = site.get("labs")
    if not labs_cfg:
        return
    ai_cfg = labs_cfg.get("ai")
    if not ai_cfg:
        if verbose:
            print("  [solve] no ai config, skipping", file=sys.stderr)
        return

    provider = ai_cfg.get("provider", "opencode")
    model = ai_cfg.get("model", "deepseek-v4-pro")
    output_dir = Path(ai_cfg.get("output_dir", "output/solutions"))
    lab_file = Path(labs_cfg.get("output_file", "last-lab-content.txt"))

    if not lab_file.exists():
        if verbose:
            print(f"  [solve] lab file not found: {lab_file}, skipping",
                  file=sys.stderr)
        return

    if provider in ("opencode", "openai"):
        base_url = ai_cfg.get("base_url")
        api_key = os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(json.dumps({"error": f"Site '{site['name']}': --solve requires OPENCODE_API_KEY or OPENAI_API_KEY env var"}),
                  file=sys.stderr)
            result = {"solved": [], "failed": ["missing_api_key"]}
            if notifier:
                try:
                    notifier.notify_solutions_saved(site["name"], output_dir,
                                                    result["solved"],
                                                    result["failed"],
                                                    verbose=verbose)
                except Exception as exc:
                    if verbose:
                        print(f"  [notify] error: {exc}", file=sys.stderr)
            return result
        client = OpenAIClient(model=model, base_url=base_url)
    elif provider == "ollama":
        base_url = ai_cfg.get("base_url")
        client = OllamaClient(model=model, base_url=base_url)
    else:
        if verbose:
            print(f"  [solve] unknown provider '{provider}', skipping",
                  file=sys.stderr)
        return

    solver = LabSolver(client=client, model=model, output_dir=output_dir)
    result = solver.solve(lab_file, verbose=verbose)
    if notifier and result:
        try:
            notifier.notify_solutions_saved(site["name"], output_dir,
                                            result.get("solved", []),
                                            result.get("failed", []),
                                            verbose=verbose)
        except Exception as exc:
            if verbose:
                print(f"  [notify] error: {exc}", file=sys.stderr)
    return result


def _run_scrape_only(driver, site: dict, cookies_file: Path, verbose: bool,
                     name: str, solve: bool = False,
                     notifier=None) -> dict:
    cookies = load_cookies(cookies_file)
    scrape_cfg = site.get("scrape", {})
    base_url = scrape_cfg.get("target_url") or site["url"]
    if verbose:
        print(f"  [cookies] loading {len(cookies)} cookie(s) from {cookies_file}", file=sys.stderr)
    apply_cookies(driver, cookies, base_url)

    navigate_steps = site.get("navigate")
    if navigate_steps:
        nav = Navigator(driver, navigate_steps)
        nav.run(verbose)

    scraper = Scraper(driver)
    data = scraper.scrape(scrape_cfg, verbose)
    _process_labs(driver, site, verbose, notifier=notifier)
    if solve:
        _process_solve(site, verbose, notifier=notifier)
    return _build_result(name, "success", data)


def process_site(site: dict, verbose: bool, scrape_only: bool = False,
                 cookies_file: Path | None = None,
                 save_cookies_path: Path | None = None,
                 solve: bool = False,
                 notifier=None) -> dict:
    name = site["name"]
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        driver = None
        try:
            driver = create_driver()

            if scrape_only and cookies_file:
                return _run_scrape_only(driver, site, cookies_file, verbose, name,
                                       solve=solve, notifier=notifier)

            ok, msg = do_login(driver, site, verbose)

            if ok:
                if save_cookies_path:
                    if verbose:
                        print(f"  [cookies] saving to {save_cookies_path}", file=sys.stderr)
                    save_cookies(driver, save_cookies_path)

                navigate_steps = site.get("navigate")
                if navigate_steps:
                    nav = Navigator(driver, navigate_steps)
                    nav.run(verbose)

                scraper = Scraper(driver)
                scrape_cfg = site.get("scrape", {})
                data = scraper.scrape(scrape_cfg, verbose)
                _process_labs(driver, site, verbose, notifier=notifier)
                if solve:
                    _process_solve(site, verbose, notifier=notifier)
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
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="Automated website login + scraping")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"Path to config JSON (default: {DEFAULT_CONFIG})")
    parser.add_argument("--site", help="Only process the named site")
    parser.add_argument("--no-verbose", action="store_true",
                        help="Suppress debug output")
    parser.add_argument("--scrape-only", action="store_true",
                        help="Skip login; reuse session via --cookies-file")
    parser.add_argument("--solve", action="store_true",
                        help="Send scraped lab content to AI and save solution files")
    parser.add_argument("--cookies-file", type=Path,
                        help="Path to JSON cookies file (required with --scrape-only)")
    parser.add_argument("--save-cookies", type=Path,
                        help="Save session cookies to a JSON file after successful login")
    parser.add_argument("--report-file", type=Path,
                        help="Append human-readable report to a file (default: stderr)")
    parser.add_argument("--notify", action="store_true",
                        help="Send Telegram notifications on lab/solve completion")
    parser.add_argument("--telegram-config", type=Path,
                        default="config/telegram.json",
                        help="Path to Telegram bot config JSON (default: config/telegram.json)")
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

    notifier = None
    if args.notify:
        telegram_config_path = args.telegram_config
        if not telegram_config_path.exists():
            print(json.dumps({"error": f"Telegram config not found: {telegram_config_path}"}),
                  file=sys.stderr)
            sys.exit(1)
        try:
            telegram_cfg = load_telegram_config(telegram_config_path)
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"error": f"Telegram config read error: {e}"}), file=sys.stderr)
            sys.exit(1)
        notifier = create_notifier(telegram_cfg)

    overall = "success"
    for site in sites:
        if verbose:
            print(f"=== Processing: {site['name']} ===", file=sys.stderr)
        result = process_site(site, verbose,
                              scrape_only=args.scrape_only,
                              cookies_file=args.cookies_file,
                              save_cookies_path=args.save_cookies,
                              solve=args.solve,
                              notifier=notifier)
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