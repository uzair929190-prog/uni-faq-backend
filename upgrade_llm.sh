
TARGET="$HOME/uni-faq/backend"
cd "$TARGET"
echo ">>> Folder: $TARGET"

if [ -x "$TARGET/venv/bin/python" ]; then PY="$TARGET/venv/bin/python"; else PY="python3"; fi

# ---------- app/config.py ----------
cat > app/config.py << 'EOF'
# ===== config.py : saari settings ek jagah (baqi files yahan se import karti hain) =====
import os                                    # os = environment variables parhne ke liye
from pathlib import Path                     # Path = file/folder ke raaste handle karna
from dotenv import load_dotenv               # .env file load karne wali library

# __file__ = ye file; .parent.parent = do folder upar = backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")               # .env ke variables memory mein aa gaye

class Settings:
    # ---- embeddings (candidates nikalne ke liye) ----
    MODEL_NAME = os.getenv("MODEL_NAME", "intfloat/multilingual-e5-small")
    QUERY_PREFIX = os.getenv("QUERY_PREFIX", "query: ")        # e5 ko ye prefixes chahiye
    PASSAGE_PREFIX = os.getenv("PASSAGE_PREFIX", "passage: ")
    THRESHOLD = float(os.getenv("THRESHOLD", 0.0))             # sirf tab kaam aata hai jab LLM band ho
    W_SEM = float(os.getenv("W_SEM", 1.0))                     # 1.0 = sirf meaning
    # ---- Groq LLM (sahi FAQ chunne ke liye) ----
    USE_LLM = os.getenv("USE_LLM", "1") == "1"                 # "0" likho to LLM band
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")               # key sirf .env mein, code mein kabhi nahi
    GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    CANDIDATES = int(os.getenv("CANDIDATES", 25))              # embeddings ke top-N FAQs LLM ko jate hain
    # ---- baqi ----
    ADMIN_KEY = os.getenv("ADMIN_KEY", "changeme")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    FAQ_CSV = BASE_DIR / "data" / "faqs.csv"
    LOG_DIR = BASE_DIR / "logs"

settings = Settings()    # ek hi object poori app mein use hoga
EOF

# ---------- app/services/llm_matcher.py ----------
cat > app/services/llm_matcher.py << 'EOF'
# ===== llm_matcher.py : Groq LLM se bataya jata hai ke kaun sa FAQ sahi hai =====
# LLM jawab KHUD nahi likhta. Wo sirf FAQ ka number chunta hai (ya 0 = koi nahi).
# Jawab hamesha tumhari CSV ka hota hai, isliye galat jawab nahi ban sakta.
import hashlib, json, re, time
import urllib.request, urllib.error
from app.config import settings

class LLMError(Exception):
    pass

SYSTEM = (
    "You are the FAQ matcher of a university chatbot. A student asks a question in English, Urdu or Roman Urdu. "
    "Below is a list of FAQ entries, each written as: id | category | typical question. "
    "Choose the id of the FAQ whose answer would directly answer the student's question. "
    "Pay attention to details such as semester number, degree name, fee type (tuition vs hostel vs late fee). "
    "If no FAQ answers the question, or the question is unrelated to the university, choose 0. "
    'Reply only with JSON like {"id": 12}.'
)

class LLMMatcher:
    def __init__(self):
        self.cache_path = settings.LOG_DIR / "llm_cache.json"   # same sawal dobara aaye to API call nahi
        self.cache = {}
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}
        self.drop = set()        # jo extra fields model ko pasand nahi aaye, yahan jama hote hain
        self.min_gap = 0.0       # do API calls ke beech kam az kam itne second (evaluate rate limit ke liye)
        self.retry_429 = 0       # live server: 429 pe wait nahi; evaluate: kai dafa wait
        self.last_call = 0.0
        self.last_error = ""
        self.api_calls = 0

    @property
    def enabled(self):
        return settings.USE_LLM and bool(settings.GROQ_API_KEY)

    def choose(self, question, candidates):
        """candidates = [(id, category, question_text), ...]  ->  chuna hua id ya 0"""
        ids = [c[0] for c in candidates]
        raw = settings.LLM_MODEL + "|" + question + "|" + ",".join(str(i) for i in ids)
        key = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        if key in self.cache:                                   # cache hit
            return self.cache[key]
        lines = "\n".join(f"{i} | {cat} | {q}" for i, cat, q in candidates)
        user = f"FAQ list:\n{lines}\n\nStudent question: {question}"
        chosen = self._parse(self._post(user), ids)
        self.cache[key] = chosen
        try:
            settings.LOG_DIR.mkdir(exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache), encoding="utf-8")
        except Exception:
            pass
        return chosen

    @staticmethod
    def _parse(content, ids):
        val = None
        try:
            val = int(json.loads(content)["id"])
        except Exception:
            m = re.search(r'"?id"?\s*[:=]\s*(\d+)', content or "") or re.search(r"\d+", content or "")
            if m:
                val = int(m.group(m.lastindex or 0))
        if val is None or (val != 0 and val not in ids):
            raise LLMError(f"LLM ka jawab samajh nahi aaya: {content!r}")
        return val

    def _post(self, user):
        body = {
            "model": settings.LLM_MODEL,
            "temperature": 0,
            "max_completion_tokens": 800,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            # strict JSON: model sirf {"id": number} de sakta hai
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "faq_choice", "strict": True,
                "schema": {"type": "object", "properties": {"id": {"type": "integer"}},
                           "required": ["id"], "additionalProperties": False}}},
            "reasoning_effort": "low",     # kam sochna = kam tokens (agar model na maane to neeche drop ho jata hai)
        }
        url = settings.GROQ_BASE_URL.rstrip("/") + "/chat/completions"
        n429 = 0
        for _ in range(8):
            for k in self.drop:
                body.pop(k, None)
            gap = self.min_gap - (time.time() - self.last_call)
            if gap > 0:
                time.sleep(gap)                                  # rate limit se bachne ke liye
            self.last_call = time.time()
            req = urllib.request.Request(
                url, data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + settings.GROQ_API_KEY,
                         "User-Agent": "uni-faq-backend/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = json.loads(r.read().decode("utf-8"))
                self.api_calls += 1
                return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "ignore")[:300]
                if e.code == 429:                                # bohat zyada requests
                    n429 += 1
                    if n429 > self.retry_429:
                        self.last_error = "HTTP 429 (rate limit): " + detail
                        raise LLMError(self.last_error)
                    try:
                        wait = float(e.headers.get("retry-after") or 20)
                    except ValueError:
                        wait = 20.0
                    time.sleep(min(wait + 1, 65))
                    continue
                if e.code == 400 and "reasoning_effort" in body:     # model ye field nahi maanta
                    self.drop.add("reasoning_effort")
                    continue
                if e.code == 400 and "response_format" in body:      # model strict JSON nahi maanta
                    self.drop.add("response_format")
                    continue
                self.last_error = f"HTTP {e.code}: {detail}"
                raise LLMError(self.last_error)
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
                self.last_error = f"{type(e).__name__}: {e}"
                raise LLMError(self.last_error)
        self.last_error = "bohat retries ke baad bhi fail"
        raise LLMError(self.last_error)
EOF

# ---------- app/services/nlp_engine.py ----------
cat > app/services/nlp_engine.py << 'EOF'
# ===== nlp_engine.py : embeddings se candidates, phir LLM se sahi FAQ =====
import re
import numpy as np                                    # numpy = tez math
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from app.config import settings
from app.services.llm_matcher import LLMMatcher, LLMError

def tokenize(text: str):
    return re.findall(r"\w+", text.lower())           # punctuation hata ke alfaaz alag

class NLPEngine:
    def __init__(self, store):
        self.store = store
        self.llm = LLMMatcher()                       # Groq wala hissa
        # model load (pehli dafa internet se download hoga, phir cache se)
        self.model = SentenceTransformer(settings.MODEL_NAME)
        self.rebuild_index()                          # sab FAQ rows ke vectors banao

    def _encode(self, texts, prefix):
        # normalize_embeddings=True => vectors ki lambai 1, to dot product = cosine similarity
        return np.asarray(self.model.encode([prefix + t for t in texts],
                                            normalize_embeddings=True, show_progress_bar=False))

    def rebuild_index(self):
        # FAQs badlein (naya add ho) to ye dobara chalta hai
        self.texts = [f["question"] + " " + f["answer"] for f in self.store.faqs]
        self.emb = self._encode(self.texts, settings.PASSAGE_PREFIX)        # FAQ rows ke vectors
        self.bm25 = BM25Okapi([tokenize(t) for t in self.texts])            # keyword index
        self.groups = {}                                                    # jawab -> uski saari paraphrase rows
        for f in self.store.faqs:
            self.groups.setdefault(f["answer"], []).append(f)

    def search(self, question: str, category: str = None, top_k: int = 3):
        faqs = self.store.faqs
        q = self._encode([question], settings.QUERY_PREFIX)[0]              # sawal ka vector
        sem = self.emb @ q                                                  # semantic score (cosine)
        w = settings.W_SEM
        if w < 1.0:                                                         # keywords sirf tab jab weight ho
            kw = np.maximum(np.array(self.bm25.get_scores(tokenize(question))), 0)
            kw = kw / max(kw.max(), 1e-9)
            score = w * sem + (1 - w) * kw
        else:
            score = sem
        best = {}                                                           # jawab -> (score, faq row)
        for i, f in enumerate(faqs):
            if category and f["category"] != category:                      # category filter
                continue
            a = f["answer"]
            if a not in best or score[i] > best[a][0]:                      # same jawab ki paraphrases mein se best
                best[a] = (float(score[i]), f)
        ranked = sorted(best.values(), key=lambda x: x[0], reverse=True)[:top_k]
        return [(f, s) for s, f in ranked]                                  # [(faq, score), ...]

    def answer(self, question: str, category: str = None):
        """Poora faisla: dict {matched, score, suggestions, source}. matched=None => jawab nahi mila."""
        cands = self.search(question, category, top_k=max(settings.CANDIDATES, 3))
        if not cands:
            return {"matched": None, "score": 0.0, "suggestions": [], "source": "none"}
        if self.llm.enabled:
            try:
                # har candidate group ka pehla (representative) sawal LLM ko dikhao
                rep = lambda f: self.groups[f["answer"]][0]
                cl = [(int(rep(f)["id"]), f["category"], rep(f)["question"]) for f, _ in cands]
                cid = self.llm.choose(question, cl)
                if cid == 0:                                                # LLM: koi FAQ match nahi
                    return {"matched": None, "score": cands[0][1],
                            "suggestions": [f for f, _ in cands[:3]], "source": "llm"}
                for f, s in cands:
                    if int(rep(f)["id"]) == cid:
                        others = [x for x, _ in cands if x is not f][:2]
                        return {"matched": f, "score": s, "suggestions": others, "source": "llm"}
            except LLMError:
                pass                                                        # LLM fail => embeddings par wapas
        best, score = cands[0]
        matched = best if score >= settings.THRESHOLD else None
        return {"matched": matched, "score": score,
                "suggestions": [f for f, _ in cands[1:3]] if matched else [f for f, _ in cands[:3]],
                "source": "embedding"}
EOF

# ---------- app/schemas.py ----------
cat > app/schemas.py << 'EOF'
# ===== schemas.py : API ke input/output ka format (Pydantic khud validate karta hai) =====
from typing import List, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):            # frontend ye bhejega
    question: str                        # zaroori: user ka sawal
    category: Optional[str] = None       # optional: khali (None) bhi ho sakta hai

class Suggestion(BaseModel):             # "kya aap ye poochna chahte the?" ka ek item
    id: int
    question: str

class ChatResponse(BaseModel):           # backend ye wapas bhejega
    answered: bool                       # True = jawab mila, False = fallback
    answer: str
    confidence: float                    # embedding similarity (0 se 1); LLM ke faisle ka sabut nahi
    source: Optional[str] = None         # "llm" = LLM ne chuna, "embedding" = sirf similarity
    faq_id: Optional[int] = None
    matched_question: Optional[str] = None
    category: Optional[str] = None
    suggestions: List[Suggestion] = []   # shuru mein khali list

class FeedbackRequest(BaseModel):        # thumbs up/down
    question: str
    faq_id: Optional[int] = None
    helpful: bool                        # True = up, False = down

class NewFAQ(BaseModel):                 # admin naya FAQ add kare
    category: str
    question: str
    answer: str
EOF

# ---------- app/api/routes.py ----------
cat > app/api/routes.py << 'EOF'
# ===== routes.py : API ke saare endpoints (URLs) =====
from fastapi import APIRouter, Header, HTTPException, Request
from app.config import settings
from app.schemas import ChatRequest, ChatResponse, FeedbackRequest, NewFAQ, Suggestion
from app.utils.logger import log_jsonl

router = APIRouter()      # endpoints ka group

def _sug(rows):
    return [Suggestion(id=int(f["id"]), question=f["question"]) for f in rows]

@router.get("/health")                                   # GET /health : server zinda hai?
def health(request: Request):
    return {"status": "ok", "faqs": len(request.app.state.store.faqs),
            "llm": request.app.state.engine.llm.enabled}

@router.get("/categories")                               # GET /categories : sidebar/chips ke liye
def categories(request: Request):
    return request.app.state.store.categories()

@router.post("/chat", response_model=ChatResponse)       # POST /chat : main endpoint
def chat(req: ChatRequest, request: Request):
    r = request.app.state.engine.answer(req.question, req.category)
    if r["source"] == "none":
        raise HTTPException(404, "No FAQs found for this category")
    score = round(r["score"], 3)
    m = r["matched"]

    if m is None:                       # jawab nahi mila: guess mat karo
        log_jsonl("unanswered.jsonl", {"question": req.question, "score": score, "source": r["source"]})
        return ChatResponse(
            answered=False, confidence=score, source=r["source"],
            answer="Sorry, I couldn't find an exact answer. Did you mean one of these?",
            suggestions=_sug(r["suggestions"]))

    return ChatResponse(
        answered=True, confidence=score, source=r["source"], answer=m["answer"],
        faq_id=int(m["id"]), matched_question=m["question"], category=m["category"],
        suggestions=_sug(r["suggestions"]))

@router.post("/feedback")                                # POST /feedback : thumbs up/down
def feedback(req: FeedbackRequest):
    log_jsonl("feedback.jsonl", req.model_dump())
    return {"saved": True}

@router.post("/admin/faq")                               # POST /admin/faq : sirf admin
def add_faq(new: NewFAQ, request: Request, x_api_key: str = Header(None)):
    if x_api_key != settings.ADMIN_KEY:                  # header mein sahi password chahiye
        raise HTTPException(401, "Invalid admin key")
    row = request.app.state.store.add(new.category, new.question, new.answer)
    request.app.state.engine.rebuild_index()             # naya FAQ search mein aa jaye
    return {"added": True, "id": row["id"]}
EOF

# ---------- scripts/evaluate_llm.py ----------
cat > scripts/evaluate_llm.py << 'EOF'
# ===== evaluate_llm.py : embeddings + LLM ki asli accuracy =====
# Pehle chhota test:   python -m scripts.evaluate_llm --limit 20
# Phir poora:          python -m scripts.evaluate_llm
import argparse, csv, time
from app.config import settings, BASE_DIR
from app.services.faq_store import FAQStore
from app.services.nlp_engine import NLPEngine

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=100)      # kitne test sawal chalane hain
ap.add_argument("--delay", type=float, default=7.0)    # do API calls ke beech second (free tier ki limit ke liye)
args = ap.parse_args()

store = FAQStore()
engine = NLPEngine(store)
llm = engine.llm
if not llm.enabled:
    print("GROQ_API_KEY nahi mili. .env mein GROQ_API_KEY=... likho aur USE_LLM=1 rakho.")
    raise SystemExit(1)
llm.min_gap = args.delay
llm.retry_429 = 6                                      # rate limit lage to wait karke dobara try

tests = list(csv.DictReader(open(BASE_DIR / "data" / "test_cases.csv", encoding="utf-8")))[:args.limit]
answer_of = {int(f["id"]): f["answer"] for f in store.faqs}

OFFTOPIC = ["who is the vice chancellor of harvard", "aaj mausam kaisa hai", "bitcoin ka rate kya hai",
            "pizza kahan se order karun", "cricket match ka score kya hai", "mujhe python sikhao",
            "2 plus 2 kitne hote hain", "tum kon ho"]

n_ok = n_recall = n_none = n_fallback = 0
wrong = []
t0 = time.time()
for n, t in enumerate(tests, 1):
    want = answer_of[int(t["expected_id"])]
    cands = engine.search(t["question"], top_k=settings.CANDIDATES)
    if any(f["answer"] == want for f, _ in cands):
        n_recall += 1                                  # sahi jawab candidates mein tha?
    r = engine.answer(t["question"])
    m = r["matched"]
    if r["source"] == "embedding":
        n_fallback += 1                                # LLM fail hua, embeddings ne jawab diya
    if m is None:
        n_none += 1
    if m is not None and m["answer"] == want:
        n_ok += 1
    else:
        wrong.append((t["question"], m["question"] if m else "[KOI FAQ NAHI]"))
    if n % 10 == 0:
        print(f"  {n}/{len(tests)} done, {time.time() - t0:.0f}s", flush=True)

N = len(tests)
print(f"\nModel: {settings.LLM_MODEL} | candidates: {settings.CANDIDATES} | API calls: {llm.api_calls}")
print(f"Recall@{settings.CANDIDATES} (sahi jawab candidates mein): {n_recall/N*100:.1f}%   <- LLM isse upar nahi ja sakta")
print(f"Final top-1 accuracy: {n_ok/N*100:.1f}%  ({n_ok}/{N})")
print(f"LLM ne 'koi FAQ nahi' kaha: {n_none}   |   LLM fail (embeddings par wapas): {n_fallback}")
if n_fallback:
    print(f"  !! LLM {n_fallback} dafa fail hua. Aakhri error: {llm.last_error}")

rej = 0
for q in OFFTOPIC:
    if engine.answer(q)["matched"] is None:
        rej += 1
print(f"Off-topic sawal sahi rad hue: {rej}/{len(OFFTOPIC)}")

print("\nGalat sawal (pehle 15):  sawal  ->  bot ne ye FAQ chuna")
for q, got in wrong[:15]:
    print(f"  - {q}  ->  {got}")
EOF

# ---------- .env update (key poochho, baqi settings set karo) ----------
KEY=""
if ! grep -q '^GROQ_API_KEY=.\+' .env 2>/dev/null; then
  read -rsp "Groq API key paste karo (nazar nahi aayegi, skip ke liye Enter): " KEY || KEY=""
  echo ""
fi
GROQ_KEY_IN="$KEY" "$PY" - << 'EOF'
import os
from pathlib import Path
p = Path(".env")
lines = p.read_text().splitlines() if p.exists() else []
cur = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in lines if "=" in l and not l.startswith("#")}
force = {"W_SEM": "1.0", "THRESHOLD": "0.0"}                       # embeddings ke nateeje se
default = {"USE_LLM": "1", "LLM_MODEL": "openai/gpt-oss-20b", "CANDIDATES": "25", "GROQ_API_KEY": ""}
cur.update(force)
for k, v in default.items():
    cur.setdefault(k, v)
if os.environ.get("GROQ_KEY_IN"):
    cur["GROQ_API_KEY"] = os.environ["GROQ_KEY_IN"].strip()
p.write_text("\n".join(f"{k}={v}" for k, v in cur.items()) + "\n")
masked = {k: ("***" if k == "GROQ_API_KEY" and v else v) for k, v in cur.items()}
print(masked)
EOF

echo ""
echo "=== UPGRADE MUKAMMAL ==="
"$PY" -m py_compile app/config.py app/services/llm_matcher.py app/services/nlp_engine.py app/api/routes.py app/schemas.py scripts/evaluate_llm.py && echo "Python files theek hain"
echo "Agla step:  python -m scripts.evaluate_llm --limit 20"