# ===== translate_answers.py : makes the Urdu + Roman Urdu version of every FAQ answer (run ONCE) =====
#   python -m scripts.translate_answers            (translates everything that is missing, safe to re-run)
# Result: data/translations.json   (English answer -> {"ur": ..., "roman": ...})
# The chatbot only reads this file, so there is no extra API call while chatting.
import json, re, time
from app.config import settings
from app.services.faq_store import FAQStore
from app.services.llm_matcher import LLMMatcher, LLMError

llm = LLMMatcher()
if not llm.enabled:
    print("GROQ_API_KEY not found. Put GROQ_API_KEY=... in .env and keep USE_LLM=1.")
    raise SystemExit(1)
llm.min_gap = 3.0                     # seconds between calls (free-tier limit)
llm.retry_429 = 6                     # if the rate limit hits, wait and try again

path = settings.FAQ_CSV.parent / "translations.json"
done = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
answers = sorted({f["answer"] for f in FAQStore().faqs})
todo = [a for a in answers if a not in done]
print(f"{len(answers)} unique answers, {len(todo)} still to translate")

def numbers_ok(src, t):
    """Every number of the English answer must appear unchanged in the translation."""
    need = re.findall(r"\d+", src)
    for version in (t["ur"], t["roman"]):
        have = re.findall(r"\d+", version)
        if any(need.count(n) > have.count(n) for n in set(need)):
            return False
    return True

bad = []
for n, a in enumerate(todo, 1):
    t = None
    for attempt in range(2):          # one retry if a number got changed
        try:
            cand = llm.translate(a)
        except LLMError as e:
            print("  error:", str(e)[:120])
            continue
        if numbers_ok(a, cand):
            t = cand
            break
    if t is None:
        bad.append(a)                 # the chatbot will simply answer these in English
        continue
    done[a] = t
    path.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")   # save after every answer
    if n % 10 == 0:
        print(f"  {n}/{len(todo)} done", flush=True)

print(f"\nTranslated: {len(done)}/{len(answers)}   Skipped (numbers did not match): {len(bad)}")
for a in bad:
    print("  skipped:", a[:80])
print("\nSample (check them with your own eyes):")
for a in list(done)[:3]:
    print("  EN   :", a[:100]); print("  UR   :", done[a]["ur"][:100]); print("  ROMAN:", done[a]["roman"][:100]); print()
