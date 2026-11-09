# ===== logger.py : unanswered aur feedback ko .jsonl file mein save karna =====
import json, time
from app.config import settings

def log_jsonl(filename: str, record: dict):
    settings.LOG_DIR.mkdir(exist_ok=True)                  # logs/ na ho to bana do
    record["time"] = time.strftime("%Y-%m-%d %H:%M:%S")    # abhi ka waqt record mein
    # "a" = append mode: purana data delete nahi hota, neeche naya add hota hai
    with open(settings.LOG_DIR / filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")   # ek line = ek record
