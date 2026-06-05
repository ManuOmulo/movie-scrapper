"""
newtoxic.com - Latest Updates Scraper
Filters to TV Series and Movies only.
"""

import json
import os
import time
import argparse
from datetime import date
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
BASE_URL      = "https://newtoxic.com/recently_added/"
DEFAULT_PAGES = 2
OUTPUT_FILE   = "data/movies.json"

# Only these category codes will be saved — everything else is dropped
ALLOWED_CATEGORIES = {"TV", "MOV"}

CATEGORY_MAP = {
    "TV":  "TV Series",
    "MOV": "Movie",
}

# ─────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────
def parse_entry_text(raw_text: str) -> dict | None:
    """
    Parse anchor text like "The Chi -> TV -> S08E03".
    Returns None if the category is not in ALLOWED_CATEGORIES.
    """
    parts = [p.strip() for p in raw_text.split("->")]

    title    = parts[0] if len(parts) > 0 else raw_text.strip()
    cat_code = parts[1].strip().upper() if len(parts) > 1 else ""
    episode  = parts[2] if len(parts) > 2 else ""

    # Drop anything that isn't TV or Movie
    if cat_code not in ALLOWED_CATEGORIES:
        return None

    return {
        "title":    title.strip(),
        "category": CATEGORY_MAP[cat_code],
        "episode":  episode.strip(),
    }


def normalize_link(href: str) -> str:
    if not href:
        return ""
    return href if href.startswith("http") else "https://newtoxic.com" + href


def normalize_image(src: str) -> str:
    if not src:
        return ""
    return src if src.startswith("http") else "https://newtoxic.com" + src


# ─────────────────────────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────────────────────────
def scrape_page(page, url: str) -> list[dict]:
    entries = []
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        page.wait_for_selector("ul[data-role='listview']", timeout=10000)

        items = page.query_selector_all("li.ui-li-has-thumb")
        print(f"  ✓ Found {len(items)} raw items on: {url}")

        for item in items:
            try:
                entry = extract_entry(item)
                if entry:
                    entries.append(entry)
            except Exception as e:
                print(f"  ⚠  Skipping one item: {e}")

    except PlaywrightTimeout:
        print(f"  ✗ Timeout loading: {url}")

    return entries


def extract_entry(item) -> dict | None:
    date_el  = item.query_selector("p")
    raw_date = date_el.inner_text().strip().replace(" ->", "").strip() if date_el else ""

    anchor = item.query_selector("a")
    if not anchor:
        return None

    href     = anchor.get_attribute("href") or ""
    raw_text = anchor.inner_text().strip()

    img_el      = anchor.query_selector("img")
    img_src     = img_el.get_attribute("src") or "" if img_el else ""
    episode_alt = img_el.get_attribute("alt") or "" if img_el else ""

    parsed = parse_entry_text(raw_text)
    if parsed is None:  # filtered out category
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


def scrape_all(pages: int = DEFAULT_PAGES, today_only: bool = False) -> list[dict]:
    today_str   = date.today().strftime("%Y/%m/%d")
    all_entries = []

    print(f"\n🎬 Scraping {pages} page(s) — TV Series & Movies only")
    print(f"   Today: {today_str}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        browser_page = context.new_page()

        for page_num in range(1, pages + 1):
            url = BASE_URL if page_num == 1 else f"{BASE_URL}?page={page_num}"
            print(f"📄 Page {page_num}/{pages}")
            page_entries = scrape_page(browser_page, url)

            if today_only:
                today_entries = [e for e in page_entries if e["date_updated"] == today_str]
                all_entries.extend(today_entries)
                if len(today_entries) < len(page_entries):
                    print(f"  → Reached older entries. Stopping early.")
                    break
            else:
                all_entries.extend(page_entries)

            if page_num < pages:
                time.sleep(2)

        browser.close()

    print(f"\n✅ Kept {len(all_entries)} entries (TV Series & Movies only)")
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
    parser.add_argument("--pages", type=int, default=DEFAULT_PAGES)
    parser.add_argument("--today-only", action="store_true")
    args = parser.parse_args()

    entries = scrape_all(pages=args.pages, today_only=args.today_only)
    if entries:
        save_data(entries)
    else:
        print("⚠️  No entries scraped.")
