# 🎬 NewToxic Daily Scraper

Automatically scrapes the latest movie and series updates from [newtoxic.com](https://newtoxic.com/recently_added/) and sends email notifications.

**Features:**
- Scrapes today's updates (TV Series, Movies, Cartoons only)
- Date-based storage: `data/YYYY-MM-DD.json`
- Smart append: New entries are added to the same day's file
- Email notifications via Gmail
- Automatic cleanup of files older than 30 days
- Stops when reaching yesterday's entries

---

## 🚀 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables
Required for ScraperAPI and email notifications:
```bash
export SCRAPERAPI_KEY="your_scraperapi_key"
export GMAIL_ADDRESS="your_email@gmail.com"
export GMAIL_APP_PASSWORD="your_app_password"
export NOTIFY_EMAIL="recipient@example.com"  # Optional, defaults to sender
```

### 3. Run locally
```bash
python main.py
```

Skip email with:
```bash
python main.py --no-email
```

---

## ⚙️ Configuration

Settings in `scraper.py`:

| Setting | Default | Description |
|---|---|---|
| `BASE_URL` | `newtoxic.com/recently_added/` | Page to scrape |
| `MAX_PAGES` | `5` | Safety cap for pages to scrape |

---

## 📁 Output Format

Creates daily JSON files: `data/YYYY-MM-DD.json`

```json
[
  {
    "title": "Movie Title",
    "category": "Movie",
    "episode": "E01",
    "date_updated": "2024/06/14",
    "link": "https://newtoxic.com/...",
    "thumbnail": "https://...",
    "date_scraped": "2024-06-14"
  }
]
```

**Behavior:**
- First run of the day: Creates new file with today's date
- Subsequent runs: Appends only new entries to the same file
- Deduplicates by (title, date_updated, episode)

---

## 📧 Email Notifications

- Sends email with new entries since last run
- Sends "no update" email if site hasn't posted today
- HTML + plain text format
- Grouped by category (Movies, TV Series, Cartoons)

---

## 🧹 Cleanup

Automatically deletes JSON files older than 30 days after each run.
