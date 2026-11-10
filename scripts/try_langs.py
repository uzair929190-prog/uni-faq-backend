# ===== try_langs.py : test the 3 languages directly in the terminal (no server needed) =====
#   python -m scripts.try_langs
#   python -m scripts.try_langs "your own question"
import sys
from app.services.faq_store import FAQStore
from app.services.nlp_engine import NLPEngine

store = FAQStore()
engine = NLPEngine(store)
engine.llm.retry_429 = 3                      # if the rate limit hits, wait and try again
questions = sys.argv[1:] or ["What is the hostel fee?", "hostel ki fees kitni hai", "ہاسٹل کی فیس کتنی ہے"]
for q in questions:
    r = engine.answer(q)
    m = r["matched"]
    print("\nQUESTION:", q)
    print("  lang:", r["lang"], "| source:", r["source"], "| category:", m["category"] if m else None)
    print("  ANSWER:", store.answer_in(m, r["lang"]) if m else "(no answer found)")
