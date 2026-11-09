# ===== evaluate.py : accuracy + threshold sweep (report ke liye) =====
import csv
from app.config import settings, BASE_DIR
from app.services.faq_store import FAQStore
from app.services.nlp_engine import NLPEngine

store = FAQStore()
engine = NLPEngine(store)
tests = list(csv.DictReader(open(BASE_DIR / "data" / "test_cases.csv", encoding="utf-8")))
answer_of = {int(f["id"]): f["answer"] for f in store.faqs}      # id -> sahi jawab

rows = []                                   # (sawal, score, top1 sahi?, top3 mein sahi?)
for t in tests:
    res = engine.search(t["question"], top_k=3)
    want = answer_of[int(t["expected_id"])]
    rows.append((t["question"], res[0][1], res[0][0]["answer"] == want,
                 any(f["answer"] == want for f, _ in res)))

n = len(rows)
print(f"Total: {n} | Top-1 accuracy: {sum(r[2] for r in rows)/n*100:.1f}% | Top-3 accuracy: {sum(r[3] for r in rows)/n*100:.1f}%")

# threshold sweep: score kitna ho to jawab dein? Zyada threshold = kam jawab, par zyada sahi
print("\nThreshold sweep (precision = jawab diye gaye sawalon mein sahi kitne):")
print(f"{'threshold':>9} {'answered':>9} {'precision%':>10} {'coverage%':>10}")
scores = sorted(r[1] for r in rows)
lo, hi = scores[0], scores[-1]
for k in range(0, 9):
    th = lo + (hi - lo) * k / 8             # lowest se highest score tak 9 qadam
    ans = [r for r in rows if r[1] >= th]
    if ans:
        prec = sum(r[2] for r in ans) / len(ans) * 100
        print(f"{th:9.3f} {len(ans):9d} {prec:10.1f} {len(ans)/n*100:10.1f}")

print("\nGalat top-1 sawal (pehle 15):")
for q, s, ok, in3 in [r for r in rows if not r[2]][:15]:
    print(f"  - {q}  (score {s:.2f}, top3 mein sahi: {'haan' if in3 else 'nahi'})")
