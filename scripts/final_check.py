# ===== final_check.py : full backend test in the terminal (no server needed) =====
#   python -m scripts.final_check
# Uses a temporary copy of the FAQs and logs, so your real data is never touched.
# Takes about 3-4 minutes (it waits between Groq calls to respect the free-tier limit).
import csv, json, os, shutil, tempfile, threading, time
from pathlib import Path
from app.config import settings, BASE_DIR

tmp = Path(tempfile.mkdtemp())                         # temporary working copy
shutil.copy(settings.FAQ_CSV, tmp / "faqs.csv")
tr_file = settings.FAQ_CSV.parent / "translations.json"
if tr_file.exists():
    shutil.copy(tr_file, tmp / "translations.json")
real_data = settings.FAQ_CSV
settings.FAQ_CSV = tmp / "faqs.csv"                    # the admin test writes here, not to the real CSV
settings.LOG_DIR = tmp / "logs"                        # test logs go to the temp folder too

from fastapi.testclient import TestClient
from app.main import app
from app.services.llm_matcher import LLMError

GAP = float(os.environ.get("FINAL_GAP", "12"))         # seconds between Groq calls
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else f"   <-- {detail}"), flush=True)

def post(c, q, cat=None):
    t = time.time()
    r = c.post("/chat", json={"question": q, "category": cat})
    return r, time.time() - t

with TestClient(app) as c:
    llm = app.state.engine.llm
    llm.min_gap, llm.retry_429 = GAP, 6
    print("\n[1] Basic endpoints")
    r = c.get("/health").json()
    check("health ok, FAQs loaded, LLM on", r.get("status") == "ok" and r.get("faqs", 0) > 0 and r.get("llm") is True, r)
    cats = c.get("/categories").json()
    check("categories: list of strings (20+)", isinstance(cats, list) and len(cats) >= 20 and all(isinstance(x, str) for x in cats), cats)

    print("\n[2] Three languages")
    keys = {"answered", "answer", "confidence", "source", "lang", "faq_id", "matched_question", "category", "suggestions"}
    r, secs = post(c, "What is the hostel fee?"); j = r.json()
    check("English question -> lang en, Hostel, number 20000", r.status_code == 200 and j["lang"] == "en" and j["category"] == "Hostel" and "20000" in j["answer"], j)
    check("response has every field the frontend needs", keys <= set(j), set(j))
    check("source is llm", j["source"] == "llm", j["source"])
    r, _ = post(c, "hostel ki fees kitni hai"); j = r.json()
    check("Roman Urdu question -> lang roman, number 20000", j["lang"] == "roman" and "20000" in j["answer"], j)
    r, _ = post(c, "ہاسٹل کی فیس کتنی ہے"); j = r.json()
    check("Urdu question -> lang ur, number 20000", j["lang"] == "ur" and "20000" in j["answer"], j)
    check("Urdu answer is written in Urdu script", any("\u0600" <= ch <= "\u06ff" for ch in j["answer"]), j["answer"][:60])

    print("\n[3] Off-topic, empty, long and strange input (must never crash)")
    r, _ = post(c, "What is the weather today?"); j = r.json()
    check("off-topic -> answered false + suggestions", r.status_code == 200 and j["answered"] is False and len(j["suggestions"]) <= 3, j)
    r, _ = post(c, "fee", "Hostel")
    check("valid category filter works", r.status_code == 200 and (not r.json()["answered"] or r.json()["category"] == "Hostel"), r.text[:100])
    r, _ = post(c, "fee", "NoSuchCategory")
    check("unknown category -> 404", r.status_code == 404, r.status_code)
    r, _ = post(c, "")
    check("empty question -> no server error", r.status_code < 500, r.status_code)
    r, _ = post(c, "hostel fee " * 150)
    check("very long question -> no server error", r.status_code < 500, r.status_code)
    for weird in ["'; DROP TABLE faqs; --", "<script>alert(1)</script> fee", "😀😀 hostel 🎓"]:
        r, _ = post(c, weird)
        check(f"strange input {weird[:18]!r} -> no server error", r.status_code < 500, r.status_code)
    check("missing field -> 422", c.post("/chat", json={}).status_code == 422)
    check("wrong type -> 422", c.post("/chat", json={"question": 123}).status_code == 422)

    print("\n[4] Feedback, logs and admin")
    check("feedback saved", c.post("/feedback", json={"question": "t", "faq_id": 1, "helpful": True}).json() == {"saved": True})
    check("feedback with missing field -> 422", c.post("/feedback", json={"question": "t"}).status_code == 422)
    check("feedback + unanswered logs written", (settings.LOG_DIR / "feedback.jsonl").exists() and (settings.LOG_DIR / "unanswered.jsonl").exists())
    new = {"category": "Hostel", "question": "zzqx unique test question", "answer": "TESTANSWER zzqx"}
    check("admin: wrong key -> 401", c.post("/admin/faq", json=new, headers={"x-api-key": "wrong"}).status_code == 401)
    check("admin: no key -> 401", c.post("/admin/faq", json=new).status_code == 401)
    r = c.post("/admin/faq", json=new, headers={"x-api-key": settings.ADMIN_KEY})
    check("admin: correct key adds an FAQ", r.status_code == 200 and r.json().get("added") is True, r.text[:100])
    top = app.state.engine.search(new["question"], top_k=1)
    check("new FAQ is searchable right away", top and top[0][0]["answer"] == new["answer"], top[:1])

    print("\n[5] Robustness")
    real_post = llm._post
    def broken(*a, **k):
        raise LLMError("simulated Groq outage")
    llm._post = broken                                   # pretend Groq is down
    r, _ = post(c, "how can I get a transcript copy"); j = r.json()
    check("Groq down -> still answers from embeddings", r.status_code == 200 and j["source"] == "embedding", j)
    llm._post = real_post
    before = llm.api_calls
    post(c, "What is the hostel fee?")
    check("same question again -> cache, no new API call", llm.api_calls == before, (before, llm.api_calls))
    codes = []
    def hit():
        codes.append(c.get("/health").status_code)
        codes.append(c.post("/chat", json={"question": "What is the hostel fee?"}).status_code)
    threads = [threading.Thread(target=hit) for _ in range(8)]
    [t.start() for t in threads]; [t.join() for t in threads]
    check("8 parallel users (cached question) -> all 200", len(codes) == 16 and set(codes) == {200}, codes)
    h = c.options("/chat", headers={"Origin": "https://myapp.lovable.app", "Access-Control-Request-Method": "POST"})
    check("CORS allows a Lovable site", h.headers.get("access-control-allow-origin") in ("*", "https://myapp.lovable.app"), dict(h.headers))
    check("answer time under 20 s", secs < 20, f"{secs:.1f}s")

print("\n[6] Data files")
rows = list(csv.DictReader(open(real_data, encoding="utf-8")))
ids = [r["id"] for r in rows]
check("FAQ ids are unique", len(ids) == len(set(ids)))
check("no empty question / answer / category", all(r["question"].strip() and r["answer"].strip() and r["category"].strip() for r in rows))
tests = list(csv.DictReader(open(BASE_DIR / "data" / "test_cases.csv", encoding="utf-8")))
check("every test case points to an existing FAQ id", all(t["expected_id"] in ids for t in tests))
if tr_file.exists():
    tr = json.loads(tr_file.read_text(encoding="utf-8"))
    answers = {r["answer"] for r in rows}
    check("translations cover 95%+ of unique answers", len(answers & set(tr)) / len(answers) >= 0.95, f"{len(answers & set(tr))}/{len(answers)}")
else:
    check("translations.json exists", False, "run: python -m scripts.translate_answers")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n===== {sum(results)}/{len(results)} checks passed =====")
print("ALL GOOD: the backend is ready." if all(results) else "Some checks failed: copy the FAIL lines and send them.")
