"""
newtoxic.com - Latest Updates Scraper
Uses ScraperAPI to bypass bot detection.
Filters to TV Series, Movies and Cartoons only.
Scrapes by today's date — stops when yesterday's entries appear.
"""

import json
import os
import re
import time
import random
import argparse
from datetime import date, timedelta
from bs4 import BeautifulSoup
import requests

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
BASE_URL        = "https://newtoxic.com/recently_added/"
SCRAPERAPI_URL  = "https://api.scraperapi.com/"
OUTPUT_FILE     = "data/movies.json"
MAX_PAGES       = 5  # Safety cap

# ─────────────────────────────────────────────────────────────────
# CATEGORY MATCHING
# ─────────────────────────────────────────────────────────────────
TV_PATTERN = re.compile(r'^TV', re.IGNORECASE)

EXACT_CATEGORIES = {
    "MOV": "Movie",
    "CAR": "Cartoon",
}

def resolve_category(cat_code: str) -> str | None:
    code = cat_code.strip()
    if TV_PATTERN.match(code):
        return "TV Series"
    upper = code.upper()
    if upper in EXACT_CATEGORIES:
        return EXACT_CATEGORIES[upper]
    return None


# ─────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────
def parse_entry_text(raw_text: str) -> dict | None:
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


# ─────────────────────────────────────────────────────────────────
# SCRAPERAPI FETCH
# ─────────────────────────────────────────────────────────────────
def fetch_page(url: str, api_key: str) -> BeautifulSoup | None:
    """Fetch a page via ScraperAPI and return a BeautifulSoup object."""
    try:
        response = requests.get(
            SCRAPERAPI_URL,
            params={"api_key": api_key, "url": url},
            timeout=60,
        )
        if response.status_code == 200:
            return BeautifulSoup(response.text, "lxml")
        else:
            print(f"  ✗ ScraperAPI returned status {response.status_code} for {url}")
            return None
    except requests.exceptions.Timeout:
        print(f"  ✗ Request timed out for {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────────────────────────
def scrape_page(url: str, api_key: str) -> tuple[list[dict], bool]:
    """
    Scrape a single page via ScraperAPI.
    Returns (entries, stop_scraping).
    stop_scraping=True when we hit entries older than today.
    """
    entries       = []
    stop_scraping = False
    today_str     = date.today().strftime("%Y/%m/%d")

    soup = fetch_page(url, api_key)
    if not soup:
        return entries, stop_scraping

    items = [li for li in soup.select("ul[data-role='listview'] li") if li.select_one("a")]
    print(f"  ✓ Found {len(items)} raw items on: {url}")

    for item in items:
        try:
            entry = extract_entry(item)
            if not entry:
                continue

            entry_date = entry["date_updated"]

            # Stop as soon as we see an entry older than today
            if entry_date and entry_date != today_str:
                print(f"  → Hit date {entry_date} (not today) — stopping.")
                stop_scraping = True
                break

            entries.append(entry)

        except Exception as e:
            print(f"  ⚠  Skipping one item: {e}")

    return entries, stop_scraping


def extract_entry(item) -> dict | None:
    # Date is in the <p> tag
    date_el  = item.select_one("p")
    raw_date = date_el.get_text(strip=True).replace("->", "").strip() if date_el else ""

    anchor = item.select_one("a")
    if not anchor:
        return None

    href     = anchor.get("href", "")
    raw_text = anchor.get_text(strip=True)

    img_el      = anchor.select_one("img")
    img_src     = img_el.get("src", "") if img_el else ""
    episode_alt = img_el.get("alt", "") if img_el else ""

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
    """
    api_key = os.environ.get("SCRAPERAPI_KEY", "").strip()
    if not api_key:
        print("❌ SCRAPERAPI_KEY environment variable is not set.")
        return []

    today_str   = date.today().strftime("%Y/%m/%d")
    all_entries = []

    print(f"\n🎬 Scraping today's updates — TV Series, Movies & Cartoons")
    print(f"   Today   : {today_str}")
    print(f"   Method  : ScraperAPI\n")

    for page_num in range(1, MAX_PAGES + 1):
        url = BASE_URL if page_num == 1 else f"{BASE_URL}?page={page_num}"
        print(f"📄 Page {page_num}")

        page_entries, stop = scrape_page(url, api_key)
        all_entries.extend(page_entries)

        if stop:
            print(f"  ✓ Date boundary reached — done after {page_num} page(s).")
            break

        if page_num < MAX_PAGES:
            delay = random.uniform(1, 3)
            print(f"  ⏱  Waiting {delay:.1f}s...")
            time.sleep(delay)
    else:
        print(f"⚠️  Reached MAX_PAGES ({MAX_PAGES}) safety cap.")

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
    entries = scrape_all()
    if entries:
        save_data(entries)
    else:
        print("⚠️  No entries scraped.")
