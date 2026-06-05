"""
main.py — Entry point called by GitHub Actions and the CLI
"""

import sys
import argparse
from scraper import scrape_all, save_data, DEFAULT_PAGES
from notify import send_email

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NewToxic.com scraper")
    parser.add_argument("--pages", type=int, default=DEFAULT_PAGES,
                        help=f"Number of pages to scrape (default: {DEFAULT_PAGES})")
    parser.add_argument("--today-only", action="store_true",
                        help="Only save entries dated today")
    parser.add_argument("--no-email", action="store_true",
                        help="Skip sending the email notification")
    args = parser.parse_args()

    print("=" * 55)
    print("  🎬  NewToxic Daily Scraper")
    print("=" * 55)
    print(f"  Pages   : {args.pages}")
    print(f"  Email   : {'disabled' if args.no_email else 'enabled'}")
    print("=" * 55)

    # 1. Scrape
    entries = scrape_all(pages=args.pages, today_only=args.today_only)

    if not entries:
        print("\n❌ No entries scraped.")
        sys.exit(1)

    # 2. Save — returns only the newly added entries
    new_entries = save_data(entries)

    if new_entries:
        print("\n📋 New entries added:")
        for e in new_entries[:10]:
            ep = f" [{e['episode']}]" if e.get("episode") else ""
            print(f"   • {e['title']} ({e['category']}){ep}")
        if len(new_entries) > 10:
            print(f"   ... and {len(new_entries) - 10} more")
    else:
        print("\nℹ️  No new entries since last run.")

    # 3. Email — sends today's new entries
    if not args.no_email:
        print("\n📬 Sending email...")
        send_email(entries=new_entries)

    print("\n✅ Done!")
