"""
notify.py — Send daily scrape results via Gmail.
"""

import os
import json
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def load_todays_entries(filepath="data/movies.json") -> list[dict]:
    """Return only entries scraped today."""
    today = str(date.today())
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return [e for e in json.load(f) if e.get("date_scraped") == today]
        except json.JSONDecodeError:
            return []


def group_by_category(entries: list[dict]) -> dict:
    grouped = {}
    for e in entries:
        cat = e.get("category", "Other")
        grouped.setdefault(cat, []).append(e)
    # Always show Movies first, then TV Series
    return dict(sorted(grouped.items(), key=lambda x: (x[0] != "Movie", x[0])))


def build_email_html(entries: list[dict], today: str) -> str:
    grouped = group_by_category(entries)
    total   = len(entries)

    category_blocks = ""
    for category, items in grouped.items():
        icon = "🎬" if category == "Movie" else "📺"
        rows = ""
        for item in items:
            ep   = item.get("episode", "")
            link = item.get("link", "#")
            ep_badge = (
                f'<span style="background:#2a2a4a;color:#a1a5ff;font-size:11px;'
                f'padding:2px 7px;border-radius:10px;margin-left:8px;">{ep}</span>'
                if ep else ""
            )
            rows += f"""
            <tr style="border-bottom:1px solid #f0f0f0;">
              <td style="padding:10px 16px;">
                <a href="{link}" style="color:#1a1a2e;text-decoration:none;font-weight:500;font-size:14px;">
                  {item['title']}
                </a>{ep_badge}
              </td>
            </tr>"""

        category_blocks += f"""
        <tr>
          <td style="padding:10px 16px 4px;background:#f7f7ff;">
            <span style="font-size:13px;font-weight:700;color:#1a1a2e;
                         text-transform:uppercase;letter-spacing:1px;">
              {icon} {category} <span style="color:#a1a5ff;">({len(items)})</span>
            </span>
          </td>
        </tr>
        {rows}
        <tr><td style="height:12px;"></td></tr>"""

    return f"""
    <html><body style="margin:0;padding:20px;background:#f0f0f8;font-family:Arial,sans-serif;">
      <div style="max-width:580px;margin:0 auto;background:#fff;
                  border-radius:10px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.1);">

        <div style="background:#1a1a2e;padding:28px 24px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">🎬</div>
          <h1 style="color:#a1a5ff;margin:0;font-size:20px;letter-spacing:1px;">
            NewToxic Daily Update
          </h1>
          <p style="color:#888;margin:8px 0 0;font-size:13px;">
            {today} &nbsp;·&nbsp; <strong style="color:#fff;">{total}</strong> new titles
          </p>
        </div>

        <table style="width:100%;border-collapse:collapse;">
          {category_blocks}
        </table>

        <div style="padding:18px;text-align:center;background:#f9f9ff;
                    border-top:1px solid #eee;">
          <a href="https://newtoxic.com/recently_added/"
             style="color:#a1a5ff;font-size:12px;text-decoration:none;">
            View full list on newtoxic.com →
          </a>
        </div>
      </div>
    </body></html>"""


def build_plain_text(entries: list[dict], today: str) -> str:
    grouped = group_by_category(entries)
    lines   = [f"NewToxic Daily Update — {today}", f"{len(entries)} new titles\n"]
    for category, items in grouped.items():
        lines.append(f"{category.upper()} ({len(items)})")
        lines.append("-" * 30)
        for item in items:
            ep = f" [{item['episode']}]" if item.get("episode") else ""
            lines.append(f"  {item['title']}{ep}")
            if item.get("link"):
                lines.append(f"  {item['link']}")
        lines.append("")
    lines.append("https://newtoxic.com/recently_added/")
    return "\n".join(lines)


def send_email(entries: list[dict] = None):
    """Send today's scraped entries via Gmail."""
    sender   = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    receiver = os.environ.get("NOTIFY_EMAIL", sender)

    if not sender or not password:
        print("❌ Email: GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set.")
        return

    if entries is None:
        entries = load_todays_entries()

    today = str(date.today())
    total = len(entries)

    if total == 0:
        print("ℹ️  Email: No new entries today — skipping.")
        return

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"🎬 NewToxic — {total} new titles ({today})"
    msg["From"]    = sender
    msg["To"]      = receiver

    msg.attach(MIMEText(build_plain_text(entries, today), "plain"))
    msg.attach(MIMEText(build_email_html(entries, today), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"✅ Email sent to {receiver} — {total} titles")
    except Exception as e:
        print(f"❌ Email error: {e}")


def send_no_update_email():
    """Send a simple email when the site has no new entries yet."""
    sender   = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    receiver = os.environ.get("NOTIFY_EMAIL", sender)

    if not sender or not password:
        print("❌ Email: GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set.")
        return

    today = str(date.today())

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"🎬 NewToxic — No new updates yet ({today})"
    msg["From"]    = sender
    msg["To"]      = receiver

    plain = f"NewToxic Daily Scraper\n\nNo new entries found for {today} yet.\nThe site may not have updated. Try checking later at https://newtoxic.com/recently_added/"

    html = f"""
    <html><body style="margin:0;padding:20px;background:#f0f0f8;font-family:Arial,sans-serif;">
      <div style="max-width:580px;margin:0 auto;background:#fff;
                  border-radius:10px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.1);">
        <div style="background:#1a1a2e;padding:28px 24px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">🎬</div>
          <h1 style="color:#a1a5ff;margin:0;font-size:20px;">NewToxic Daily Update</h1>
          <p style="color:#888;margin:8px 0 0;font-size:13px;">{today}</p>
        </div>
        <div style="padding:32px;text-align:center;">
          <p style="font-size:40px;margin:0;">😴</p>
          <p style="font-size:16px;color:#333;margin:16px 0 8px;font-weight:bold;">
            No new entries yet
          </p>
          <p style="font-size:13px;color:#888;margin:0;">
            The site hasn't posted today's updates yet.
          </p>
          <a href="https://newtoxic.com/recently_added/"
             style="display:inline-block;margin-top:20px;padding:10px 24px;
                    background:#1a1a2e;color:#a1a5ff;border-radius:6px;
                    text-decoration:none;font-size:13px;">
            Check manually →
          </a>
        </div>
      </div>
    </body></html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"✅ No-update email sent to {receiver}")
    except Exception as e:
        print(f"❌ Email error: {e}")


if __name__ == "__main__":
    send_email()
