# ===== llm_matcher.py : Groq LLM se bataya jata hai ke kaun sa FAQ sahi hai =====
# LLM jawab KHUD nahi likhta. Wo sirf FAQ ka number chunta hai (ya 0 = koi nahi).
# Jawab hamesha tumhari CSV ka hota hai, isliye galat jawab nahi ban sakta.
import hashlib, json, re, time
import urllib.request, urllib.error
from app.config import settings

class LLMError(Exception):
    pass

SYSTEM = (
    "You are the FAQ matcher of a university chatbot. A student asks a question in English, Urdu or Roman Urdu "
    "(spelling can be informal). Below is a list of FAQ entries, each written as: id | category | typical question. "
    "Choose the id of the FAQ that best answers the student's question. The wording of the student's question can be "
    "very different from the FAQ, so match by meaning and topic, not by exact words. "
    "If several FAQs are related, choose the one most specific to what the student asked "
    "(check semester number, degree name, fee type such as tuition, hostel or late fee). "
    "If the question is about a university topic and one FAQ is a reasonable fit, choose it even if the match is not perfect. "
    "Choose 0 only when the question is unrelated to university life, or no FAQ covers its topic at all. "
    'Reply only with JSON like {"id": 12}.'
)
PROMPT_ID = hashlib.sha1(SYSTEM.encode("utf-8")).hexdigest()[:8]   # prompt badle to purana cache khud bekaar ho jaye

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
        raw = PROMPT_ID + "|" + settings.LLM_MODEL + "|" + question + "|" + ",".join(str(i) for i in ids)
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
