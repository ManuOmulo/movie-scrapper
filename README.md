# 🎬 NewToxic Daily Scraper

Automatically scrapes the latest movie and series updates from [newtoxic.com](https://newtoxic.com/recently_added/) every day using **Playwright** + **GitHub Actions**.

Data is saved to `data/movies.json` and committed back to this repo automatically.

---

## 🚀 Setup (One-Time)

### 1. Install dependencies locally
```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium   # Linux only
```

### 2. Discover the correct CSS selectors (REQUIRED first step)
The site uses JS rendering, so you need to inspect its actual HTML to find
the right selectors before the scraper will work properly.

```bash
python scraper.py --discover
```

This will:
- Open the site in a headless browser
- Save the full HTML to `discovered_html.html`
- Print candidate container elements to the terminal

Open `discovered_html.html` in your browser, inspect the movie card structure,
then update the `SELECTORS` dictionary in `scraper.py` accordingly.

### 3. Test the scraper locally
```bash
python main.py
```

Check `data/movies.json` for output.

### 4. Push to GitHub
```bash
git init
git add .
git commit -m "Initial scraper setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/movie-scraper.git
git push -u origin main
```

GitHub Actions will automatically pick up `.github/workflows/scrape.yml`
and start running on the daily schedule.

---

## ⚙️ Configuration

All settings are at the top of `scraper.py`:

| Setting | Default | Description |
|---|---|---|
| `BASE_URL` | `newtoxic.com/recently_added/` | The page to scrape |
| `PAGES_TO_SCRAPE` | `2` | How many pages to scrape per run |
| `SELECTORS` | (guesses) | CSS selectors — **update after running --discover** |

### Changing the schedule
Edit the cron expression in `.github/workflows/scrape.yml`:
```yaml
- cron: '0 7 * * *'   # 07:00 UTC = 10:00 AM Nairobi (UTC+3)
```
Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

---

## 📁 Output Format

`data/movies.json` — array of entries:
```json
[
  {
    "title": "Movie Title",
    "type": "Movie",
    "year": "2024",
    "link": "https://newtoxic.com/...",
    "image": "https://...",
    "date_scraped": "2024-06-04"
  }
]
```

---

## 🔧 Manual Trigger

Go to your repo → **Actions** tab → **Daily Movie Scraper** → **Run workflow**
to trigger a scrape immediately without waiting for the schedule.
