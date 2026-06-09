"""
newtoxic.com - Latest Updates Scraper
Filters to TV Series, Movies and Cartoons only.
Scrapes by today's date — stops as soon as yesterday's entries appear.
"""

import json
import os
import re
import time
import random
import argparse
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
BASE_URL     = "https://newtoxic.com/recently_added/"
OUTPUT_FILE  = "data/movies.json"
MAX_PAGES    = 10  # Safety cap — will stop earlier once it hits yesterday's date

# Heavy assets to block
BLOCKED_RESOURCES = {"image", "media", "font", "stylesheet"}

# ─────────────────────────────────────────────────────────────────
# CATEGORY MATCHING
# ─────────────────────────────────────────────────────────────────
# Regex: matches anything that STARTS with "TV" (TV, TV/S02, TV/S02-S03, etc.)
TV_PATTERN = re.compile(r'^TV', re.IGNORECASE)

EXACT_CATEGORIES = {
    "MOV": "Movie",
    "CAR": "Cartoon",
}

def resolve_category(cat_code: str) -> str | None:
    """
    Returns the display category name or None if not in our allowed list.
    TV is matched by regex so TV/S02, TV/S02-S03 etc. all resolve to 'TV Series'.
    MOV and CAR are matched exactly.
    """
    code = cat_code.strip()

    if TV_PATTERN.match(code):
        return "TV Series"

    upper = code.upper()
    if upper in EXACT_CATEGORIES:
        return EXACT_CATEGORIES[upper]

    return None  # Not in our allowed list — skip


# ─────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────
def parse_entry_text(raw_text: str) -> dict | None:
    """
    Parse anchor text like:
      "The Chi -> TV -> S08E03"
      "Blood Sisters -> TV/S02 -> Complete"
      "Gwed 2024 -> TV/S02 - S03 -> Complete"
      "Some Movie -> MOV -> 2024"
      "SpongeBob -> CAR -> S14E05"
    Returns None if category is not in our allowed list.
    """
    parts    = [p.strip() for p in raw_text.split("->")]
    title    = parts[0].strip() if len(parts) > 0 else raw_text.strip()
    cat_code = parts[1].strip() if len(parts) > 1 else ""
    episode  = parts[2].strip() if len(parts) > 2 else ""

    category = resolve_category(cat_code)
    if category is None:
        return None

    return {
        "title":    title,
        "category": category,
        "episode":  episode,
    }


def normalize_link(href: str) -> str:
    if not href:
        return ""
    return href if href.startswith("http") else "https://newtoxic.com" + href


def normalize_image(src: str) -> str:
    if not src:
        return ""
    return src if src.startswith("http") else "https://newtoxic.com" + src


def parse_site_date(raw_date: str) -> str:
    """Normalize site date '2026/06/05' to 'YYYY/MM/DD' after stripping arrows."""
    return raw_date.replace(" ->", "").strip()


# ─────────────────────────────────────────────────────────────────
# PROXY
# ─────────────────────────────────────────────────────────────────
def get_proxy_config() -> dict | None:
    """
    Reads PROXY_URL from environment variable.
    Supports multiple proxies as comma-separated list — picks one randomly.
    Format: username:password@host:port
    """
    proxy_env = os.environ.get("PROXY_URL", "").strip()
    if not proxy_env:
        return None

    proxies   = [p.strip() for p in proxy_env.split(",") if p.strip()]
    proxy_url = random.choice(proxies)

    try:
        credentials, server = proxy_url.split("@")
        username, password  = credentials.split(":", 1)
        print(f"   Proxy : {server}")
        return {
            "server":   f"http://{server}",
            "username": username,
            "password": password,
        }
    except ValueError:
        print("⚠️  PROXY_URL format invalid. Expected: user:pass@host:port")
        print("   Continuing without proxy...")
        return None


# ─────────────────────────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────────────────────────
def block_heavy_assets(route):
    if route.request.resource_type in BLOCKED_RESOURCES:
        route.abort()
    else:
        route.continue_()


def scrape_page(page, url: str) -> tuple[list[dict], bool]:
    """
    Scrape a single page.
    Returns (entries, stop_scraping).
    stop_scraping=True means we hit yesterday's date — caller should stop.
    """
    entries      = []
    stop_scraping = False
    today_str     = date.today().strftime("%Y/%m/%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y/%m/%d")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        page.wait_for_selector("ul[data-role='listview']", timeout=20000)

        items = page.query_selector_all("li.ui-li-has-thumb")
        print(f"  ✓ Found {len(items)} raw items on: {url}")

        for item in items:
            try:
                entry = extract_entry(item)
                if not entry:
                    continue

                entry_date = entry["date_updated"]

                # Stop as soon as we see yesterday's (or older) date
                if entry_date and entry_date != today_str:
                    print(f"  → Hit date {entry_date} (not today) — stopping.")
                    stop_scraping = True
                    break

                entries.append(entry)

            except Exception as e:
                print(f"  ⚠  Skipping one item: {e}")

    except PlaywrightTimeout:
        print(f"  ✗ Timeout loading: {url}")

    return entries, stop_scraping


def extract_entry(item) -> dict | None:
    date_el  = item.query_selector("p")
    raw_date = date_el.inner_text().strip() if date_el else ""
    raw_date = parse_site_date(raw_date)

    anchor = item.query_selector("a")
    if not anchor:
        return None

    href     = anchor.get_attribute("href") or ""
    raw_text = anchor.inner_text().strip()

    img_el      = anchor.query_selector("img")
    img_src     = img_el.get_attribute("src") or "" if img_el else ""
    episode_alt = img_el.get_attribute("alt") or "" if img_el else ""

    parsed = parse_entry_text(raw_text)
    if parsed is None:
        return None

    if not parsed["episode"] and episode_alt:
        parsed["episode"] = episode_alt

    return {
        "title":        parsed["title"],
        "category":     parsed["category"],
        "episode":      parsed["episode"],
        "date_updated": raw_date,
        "link":         normalize_link(href),
        "thumbnail":    normalize_image(img_src),
        "date_scraped": str(date.today()),
    }


def scrape_all() -> list[dict]:
    """
    Scrape pages until we hit yesterday's date or reach MAX_PAGES.
    No fixed page count — driven entirely by date.
    """
    today_str    = date.today().strftime("%Y/%m/%d")
    all_entries  = []
    proxy_config = get_proxy_config()

    print(f"\n🎬 Scraping today's updates — TV Series, Movies & Cartoons")
    print(f"   Today    : {today_str}")
    print(f"   Stopping : when entries older than today appear")
    print(f"   Proxy    : {'enabled ✓' if proxy_config else 'not set (running direct)'}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy=proxy_config,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Africa/Nairobi",
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        browser_page = context.new_page()
        browser_page.route("**/*", block_heavy_assets)

        for page_num in range(1, MAX_PAGES + 1):
            url = BASE_URL if page_num == 1 else f"{BASE_URL}?page={page_num}"
            print(f"📄 Page {page_num}")

            page_entries, stop = scrape_page(browser_page, url)
            all_entries.extend(page_entries)

            if stop:
                print(f"  ✓ Date boundary reached — done after {page_num} page(s).")
                break

            if page_num < MAX_PAGES:
                delay = random.uniform(2, 5)
                print(f"  ⏱  Waiting {delay:.1f}s...")
                time.sleep(delay)
        else:
            print(f"⚠️  Reached MAX_PAGES ({MAX_PAGES}) safety cap.")

        browser.close()

    print(f"\n✅ Kept {len(all_entries)} entries for today")
    return all_entries


# ─────────────────────────────────────────────────────────────────
# STORAGE
# ─────────────────────────────────────────────────────────────────
def save_data(entries: list[dict]) -> list[dict]:
    os.makedirs("data", exist_ok=True)

    existing = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    seen = {
        (e["title"], e.get("date_updated", ""), e.get("episode", ""))
        for e in existing
    }
    new_entries = [
        e for e in entries
        if (e["title"], e.get("date_updated", ""), e.get("episode", "")) not in seen
    ]

    all_data = existing + new_entries
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"💾 {len(new_entries)} new entries saved (file total: {len(all_data)})")
    return new_entries


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--today-only", action="store_true",
                        help="Alias kept for backwards compatibility — scraping is always date-based now")
    args = parser.parse_args()

    entries = scrape_all()
    if entries:
        save_data(entries)
    else:
        print("⚠️  No entries scraped.")
