# ===== tune.py : alag alag models/settings try karke accuracy ka table banata hai =====
# Chalane ka tareeqa (backend/ folder se):   python -m scripts.tune
# Pehli dafa naye models download honge (mpnet ~1.1GB, e5-small ~470MB), isliye wait karna.
import csv, re, sys, time
from pathlib import Path
import numpy as np                                   # numpy = tez math (vectors ke liye)
from rank_bm25 import BM25Okapi                      # keyword search
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parent.parent        # backend/ folder
faqs = list(csv.DictReader(open(BASE / "data" / "faqs.csv", encoding="utf-8")))
tests = list(csv.DictReader(open(BASE / "data" / "test_cases.csv", encoding="utf-8")))
ans_of = {int(r["id"]): r["answer"] for r in faqs}   # id -> sahi jawab

# (model ka naam, test-sawal ka prefix, FAQ-text ka prefix)
# e5 models ko "query: " aur "passage: " prefix chahiye hota hai, baqi ko nahi
MODELS = [
    ("paraphrase-multilingual-MiniLM-L12-v2", "", ""),        # abhi wala model
    ("paraphrase-multilingual-mpnet-base-v2", "", ""),        # bada, aksar behtar
    ("intfloat/multilingual-e5-small", "query: ", "passage: "),
]

def tok(text):
    return re.findall(r"\w+", text.lower())          # punctuation hata ke alfaaz alag

questions = [r["question"] for r in faqs]
q_plus_a = [r["question"] + " " + r["answer"] for r in faqs]   # sawal + jawab ek saath
test_q = [t["question"] for t in tests]
answers = sorted({r["answer"] for r in faqs})                  # 100 unique jawab
row_ans = [answers.index(r["answer"]) for r in faqs]           # har row kis jawab ki hai
expected = [answers.index(ans_of[int(t["expected_id"])]) for t in tests]

# BM25 (keyword) scores model se alag hain, isliye ek hi dafa nikaal lo
kw_cache = {}
for rep, texts in (("q", questions), ("qa", q_plus_a)):
    bm = BM25Okapi([tok(x) for x in texts])
    kw = np.array([bm.get_scores(tok(q)) for q in test_q])
    kw = np.maximum(kw, 0) / np.maximum(kw.max(axis=1, keepdims=True), 1e-9)   # 0 se 1 range
    kw_cache[rep] = kw

rows_out = []
for name, qp, pp in MODELS:
    print(f"\n>>> Model load: {name}", flush=True)
    t0 = time.time()
    try:
        model = SentenceTransformer(name)
    except Exception as e:                           # download na ho to is model ko skip karo
        print(f"    SKIP ({type(e).__name__}): {e}")
        continue
    enc = lambda xs, p: np.asarray(model.encode([p + x for x in xs], normalize_embeddings=True,
                                                batch_size=32, show_progress_bar=False))
    T = enc(test_q, qp)                              # test sawalon ke vectors
    for rep, texts in (("q", questions), ("qa", q_plus_a)):
        E = enc(texts, pp)                           # FAQ rows ke vectors
        sem = T @ E.T                                # cosine similarity (vectors normalized hain)
        for w in (1.0, 0.7, 0.5):                    # w = semantic ka weight, baqi keyword ka
            score = w * sem + (1 - w) * kw_cache[rep]
            best = np.full((len(test_q), len(answers)), -1.0)       # har jawab ka best score
            for j, a in enumerate(row_ans):
                best[:, a] = np.maximum(best[:, a], score[:, j])
            order = np.argsort(-best, axis=1)        # har test ke liye jawab best se worst
            top1 = np.mean([order[i][0] == expected[i] for i in range(len(test_q))]) * 100
            top3 = np.mean([expected[i] in order[i][:3] for i in range(len(test_q))]) * 100
            ok = [best[i][order[i][0]] for i in range(len(test_q)) if order[i][0] == expected[i]]
            bad = [best[i][order[i][0]] for i in range(len(test_q)) if order[i][0] != expected[i]]
            rows_out.append((name, rep, w, top1, top3,
                             float(np.mean(ok)) if ok else 0.0, float(np.mean(bad)) if bad else 0.0))
    print(f"    done in {time.time() - t0:.0f}s", flush=True)

rows_out.sort(key=lambda r: (-r[3], -r[4]))          # sab se achha upar
print("\n==== NATEEJA (top1 = pehla jawab sahi, top3 = sahi jawab pehle 3 mein) ====")
print(f"{'model':42s} {'text':4s} {'w_sem':5s} {'top1%':>6s} {'top3%':>6s} {'avg_ok':>7s} {'avg_bad':>7s}")
for n, rep, w, a1, a3, so, sb in rows_out:
    print(f"{n:42s} {rep:4s} {w:<5} {a1:6.1f} {a3:6.1f} {so:7.2f} {sb:7.2f}")

if rows_out:
    n, rep, w, a1, a3, so, sb = rows_out[0]
    print(f"\nSAB SE ACHHA: model={n} | text={'sawal' if rep == 'q' else 'sawal+jawab'} | W_SEM={w} "
          f"| top1={a1:.0f}% top3={a3:.0f}%")
    print("avg_ok = sahi jawab ka average score, avg_bad = galat jawab ka average score")
    with open(BASE / "logs" / "tune_results.csv", "w", newline="", encoding="utf-8") as f:
        (BASE / "logs").mkdir(exist_ok=True)
        w_ = csv.writer(f)
        w_.writerow(["model", "text", "w_sem", "top1", "top3", "avg_ok", "avg_bad"])
        w_.writerows(rows_out)
