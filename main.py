"""
main.py — Entry point called by GitHub Actions and the CLI
"""

import sys
from scraper import scrape_all, save_data
from notify import send_email, send_no_update_email

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NewToxic.com scraper")
    parser.add_argument("--no-email", action="store_true",
                        help="Skip sending the email notification")
    args = parser.parse_args()

    print("=" * 55)
    print("  🎬  NewToxic Daily Scraper")
    print("=" * 55)
    print(f"  Mode    : date-based (stops at yesterday's entries)")
    print(f"  Email   : {'disabled' if args.no_email else 'enabled'}")
    print("=" * 55)

    # 1. Scrape today's entries across however many pages needed
    entries = scrape_all()

    if not entries:
        print("\n ℹ️  No new entries found for today yet.")
        if not args.no_email:
            print("📬 Sending no-update email...")
            send_no_update_email()
        sys.exit(0)  # Exit cleanly — not a failure

    # 2. Save — returns only newly added entries
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

    # 3. Email
    if not args.no_email:
        print("\n📬 Sending email...")
        send_email(entries=new_entries)

    print("\n✅ Done!")
