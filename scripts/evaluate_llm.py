# ===== evaluate_llm.py : embeddings + LLM ki asli accuracy =====
#   python -m scripts.evaluate_llm --recall-only      (API ke baghair: kitne candidates chahiye?)
#   python -m scripts.evaluate_llm --limit 20         (chhota test)
#   python -m scripts.evaluate_llm --k 40             (candidates 40 karke poora test)
import argparse, csv, time
from app.config import settings, BASE_DIR
from app.services.faq_store import FAQStore
from app.services.nlp_engine import NLPEngine

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=100)       # kitne test sawal chalane hain
ap.add_argument("--delay", type=float, default=7.0)     # do API calls ke beech second (free tier ki limit ke liye)
ap.add_argument("--k", type=int, default=0)             # candidates ki ginti (0 = .env wali)
ap.add_argument("--recall-only", action="store_true")   # sirf recall dikhao, API call nahi
args = ap.parse_args()
if args.k:
    settings.CANDIDATES = args.k

store = FAQStore()
engine = NLPEngine(store)
tests = list(csv.DictReader(open(BASE_DIR / "data" / "test_cases.csv", encoding="utf-8")))[:args.limit]
answer_of = {int(f["id"]): f["answer"] for f in store.faqs}
N = len(tests)

if args.recall_only:
    print("Recall@K = sahi jawab top-K candidates mein kitni dafa aaya (LLM isse upar nahi ja sakta)")
    print("Zyada K = LLM ko zyada tokens = free tier ki limit jaldi khatam")
    for K in (10, 25, 40, 50, 70, 100):
        hit = sum(any(f["answer"] == answer_of[int(t["expected_id"])]
                      for f, _ in engine.search(t["question"], top_k=K)) for t in tests)
        print(f"  K={K:3d}: {hit/N*100:5.1f}%  ({hit}/{N})")
    raise SystemExit(0)

llm = engine.llm
if not llm.enabled:
    print("GROQ_API_KEY nahi mili. .env mein GROQ_API_KEY=... likho aur USE_LLM=1 rakho.")
    raise SystemExit(1)
llm.min_gap = args.delay
llm.retry_429 = 6                                       # rate limit lage to wait karke dobara try

OFFTOPIC = ["who is the vice chancellor of harvard", "aaj mausam kaisa hai", "bitcoin ka rate kya hai",
            "pizza kahan se order karun", "cricket match ka score kya hai", "mujhe python sikhao",
            "2 plus 2 kitne hote hain", "tum kon ho"]

n_ok = n_recall = n_fallback = 0
kinds = {"RECALL": 0, "STRICT": 0, "GALAT": 0}          # galat sawalon ki wajah
wrong = []
t0 = time.time()
for n, t in enumerate(tests, 1):
    want = answer_of[int(t["expected_id"])]
    cands = engine.search(t["question"], top_k=settings.CANDIDATES)
    in_c = any(f["answer"] == want for f, _ in cands)   # sahi jawab candidates mein tha?
    n_recall += in_c
    r = engine.answer(t["question"])
    m = r["matched"]
    if r["source"] == "embedding":
        n_fallback += 1                                 # LLM fail hua, embeddings ne jawab diya
    if m is not None and m["answer"] == want:
        n_ok += 1
    else:
        kind = "RECALL" if not in_c else ("STRICT" if m is None else "GALAT")
        kinds[kind] += 1
        wrong.append((kind, t["question"], m["question"] if m else "[KOI FAQ NAHI]"))
    if n % 10 == 0:
        print(f"  {n}/{N} done, {time.time() - t0:.0f}s", flush=True)

print(f"\nModel: {settings.LLM_MODEL} | candidates: {settings.CANDIDATES} | API calls (naye): {llm.api_calls}")
print(f"Recall@{settings.CANDIDATES} (sahi jawab candidates mein): {n_recall/N*100:.1f}%   <- LLM isse upar nahi ja sakta")
print(f"Final top-1 accuracy: {n_ok/N*100:.1f}%  ({n_ok}/{N})")
print(f"Galat sawalon ki wajah:")
print(f"  RECALL = sahi jawab candidates mein tha hi nahi        : {kinds['RECALL']}")
print(f"  STRICT = LLM ne 'koi nahi' kaha, jab ke sahi tha       : {kinds['STRICT']}")
print(f"  GALAT  = LLM ne doosra FAQ chuna (sahi candidates mein) : {kinds['GALAT']}")
if n_fallback:
    print(f"  !! LLM {n_fallback} dafa fail hua. Aakhri error: {llm.last_error}")

rej = 0
for q in OFFTOPIC:
    if engine.answer(q)["matched"] is None:
        rej += 1
print(f"Off-topic sawal sahi rad hue: {rej}/{len(OFFTOPIC)}")

print("\nGalat sawal (pehle 30):  [wajah] sawal  ->  bot ne ye FAQ chuna")
for kind, q, got in wrong[:30]:
    print(f"  [{kind}] {q}  ->  {got}")
