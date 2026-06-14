from pathlib import Path
from datetime import date, timedelta

cutoff = date.today() - timedelta(days=30)

def clean_up():
  for file in Path("data").glob("*.json"):
      try:
          file_date = date.fromisoformat(file.stem)
          if file_date < cutoff:
              file.unlink()
      except ValueError:
          pass