#!/usr/bin/env python3
"""Export your logged-in X (Twitter) session cookies for Horizon.

Launches a visible (headed) browser so you can log in to x.com, waits until
the session is authenticated (auth_token cookie present), then writes the
cookies to data/x_cookies_*.json in the format Horizon's scraper reads
(src/scrapers/twitter_playwright.py -> _load_browser_cookies).

Usage:
    uv run python scripts/export_x_cookies.py
    uv run python scripts/export_x_cookies.py --timeout 600
    uv run python scripts/export_x_cookies.py --out data/x_cookies_2.json

Notes:
    * Uses a persistent browser profile at .x_profile/ so you stay logged in
      between runs; re-running exports fresh cookies without re-logging in.
    * Only cookies for x.com / twitter.com are exported.
    * Press Ctrl+C to abort while waiting for login.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / ".x_profile"
DEFAULT_OUT = ROOT / "data" / "x_cookies_1.json"
LOGIN_URL = "https://x.com/login"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _is_logged_in(cookies: list[dict]) -> bool:
    names = {c["name"] for c in cookies}
    return "auth_token" in names and "ct0" in names


def _is_x_domain(domain: str) -> bool:
    return domain == "x.com" or domain.endswith((".x.com", "twitter.com"))


def _to_edit_this_cookie_format(cookies: list[dict]) -> list[dict]:
    """Map Playwright cookies to the browser-export format the scraper reads."""
    out = []
    for c in cookies:
        entry = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "secure": bool(c.get("secure", True)),
            "httpOnly": bool(c.get("httpOnly", False)),
        }
        expires = c.get("expires")
        if isinstance(expires, (int, float)) and expires > 0:
            entry["expirationDate"] = float(expires)
        out.append(entry)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="seconds to wait for login (default 300)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output file (default {DEFAULT_OUT.relative_to(ROOT)})",
    )
    args = parser.parse_args()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="UTC",
            color_scheme="dark",
            user_agent=USER_AGENT,
        )
        page = context.pages[0] if context.pages else context.new_page()

        cookies = context.cookies()
        if _is_logged_in(cookies):
            print("Already logged in (auth_token found) — exporting cookies.")
        else:
            print(f"\nA browser window will open. Log in at {LOGIN_URL}.")
            print(f"Waiting up to {args.timeout}s for login... (Ctrl+C to abort)\n")
            try:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                print(f"Navigation warning (ignored): {exc}")
            deadline = time.time() + args.timeout
            logged_in = False
            while time.time() < deadline:
                cookies = context.cookies()
                if _is_logged_in(cookies):
                    logged_in = True
                    print("Login detected — exporting cookies.")
                    break
                time.sleep(2)
            if not logged_in:
                print(f"Timed out after {args.timeout}s without login.")
                context.close()
                return 1

        x_cookies = [c for c in context.cookies() if _is_x_domain(c["domain"])]
        out = _to_edit_this_cookie_format(x_cookies)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {len(out)} cookies to {args.out}")
        context.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
