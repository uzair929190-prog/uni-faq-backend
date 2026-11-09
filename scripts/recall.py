# ===== recall.py : API ke baghair dekho ke kitne candidates (K) par sahi jawab milta hai =====
import csv
from app.config import BASE_DIR
from app.services.faq_store import FAQStore
from app.services.nlp_engine import NLPEngine

store = FAQStore()
engine = NLPEngine(store)
tests = list(csv.DictReader(open(BASE_DIR / "data" / "test_cases.csv", encoding="utf-8")))
answer_of = {int(f["id"]): f["answer"] for f in store.faqs}      # id -> sahi jawab

print("Recall@K = sahi jawab top-K candidates mein kitni dafa aaya (LLM isse upar nahi ja sakta)")
for K in (10, 25, 40, 50, 70, 100):
    hit = sum(any(f["answer"] == answer_of[int(t["expected_id"])]
                  for f, _ in engine.search(t["question"], top_k=K)) for t in tests)
    print(f"  K={K:3d}: {hit/len(tests)*100:5.1f}%  ({hit}/{len(tests)})")
