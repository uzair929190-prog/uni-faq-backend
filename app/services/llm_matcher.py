# ===== llm_matcher.py : asks the Groq LLM which FAQ is the right one =====
# The LLM never writes the answer itself. It only picks an FAQ id (or 0 = none).
# The answer always comes from your CSV, so the bot cannot invent a wrong answer.
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
    'Also detect the language of the student question: "en" for English, "ur" for Urdu written in Urdu script, '
    '"roman" for Urdu written in Latin letters (Roman Urdu). '
    'Reply only with JSON like {"id": 12, "lang": "roman"}.'
)

TRANSLATE_SYSTEM = (
    "You translate university FAQ answers for students in Pakistan. Produce two versions of the given English answer: "
    '"ur" = standard Urdu written in Urdu script, "roman" = Urdu written in Latin letters the way Pakistani students text '
    "(Roman Urdu). Keep every number, amount (PKR), date, percentage, name and abbreviation (CGPA, GPA, LMS, etc.) exactly as in the "
    "original, using Western digits 0-9. Do not add or remove any information. "
    'Reply only with JSON like {"ur": "...", "roman": "..."}.'
)
PROMPT_ID = hashlib.sha1(SYSTEM.encode("utf-8")).hexdigest()[:8]   # if the prompt changes, the old cache stops matching by itself

class LLMMatcher:
    def __init__(self):
        self.cache_path = settings.LOG_DIR / "llm_cache.json"   # same question again => no API call
        self.cache = {}
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}
        self.drop = set()        # extra fields the model rejected are collected here
        self.min_gap = 0.0       # minimum seconds between two API calls (to respect the rate limit)
        self.retry_429 = 0       # live server: no waiting on 429; evaluation: wait and retry several times
        self.last_call = 0.0
        self.last_error = ""
        self.api_calls = 0

    @property
    def enabled(self):
        return settings.USE_LLM and bool(settings.GROQ_API_KEY)

    def choose(self, question, candidates):
        """candidates = [(id, category, question_text), ...]  ->  (chosen id or 0, language "en"/"ur"/"roman"/None)"""
        ids = [c[0] for c in candidates]
        raw = PROMPT_ID + "|" + settings.LLM_MODEL + "|" + question + "|" + ",".join(str(i) for i in ids)
        key = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        if key in self.cache:                                   # cache hit
            return tuple(self.cache[key])
        lines = "\n".join(f"{i} | {cat} | {q}" for i, cat, q in candidates)
        user = f"FAQ list:\n{lines}\n\nStudent question: {question}"
        chosen = self._parse(self._post(user), ids)             # (id, lang)
        self.cache[key] = list(chosen)
        try:
            settings.LOG_DIR.mkdir(exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache), encoding="utf-8")
        except Exception:
            pass
        return chosen

    @staticmethod
    def _parse(content, ids):
        val, lang = None, None
        try:
            obj = json.loads(content)
            val = int(obj["id"])
            lang = obj.get("lang")
        except Exception:
            m = re.search(r'"?id"?\s*[:=]\s*(\d+)', content or "") or re.search(r"\d+", content or "")
            if m:
                val = int(m.group(m.lastindex or 0))
        if lang not in ("en", "ur", "roman"):
            lang = None
        if val is None or (val != 0 and val not in ids):
            raise LLMError(f"Could not understand the LLM reply: {content!r}")
        return val, lang

    def translate(self, answer):
        """English answer -> {"ur": ..., "roman": ...} (used once by scripts/translate_answers.py)."""
        schema = {"type": "object", "properties": {"ur": {"type": "string"}, "roman": {"type": "string"}},
                  "required": ["ur", "roman"], "additionalProperties": False}
        content = self._post("English answer:\n" + answer, system=TRANSLATE_SYSTEM, schema=schema,
                             name="translation", max_tokens=1500)
        try:
            obj = json.loads(content)
            return {"ur": str(obj["ur"]).strip(), "roman": str(obj["roman"]).strip()}
        except Exception:
            raise LLMError(f"Could not understand the translation reply: {content!r}")

    def _post(self, user, system=None, schema=None, name="faq_choice", max_tokens=800):
        body = {
            "model": settings.LLM_MODEL,
            "temperature": 0,
            "max_completion_tokens": max_tokens,
            "messages": [{"role": "system", "content": system or SYSTEM}, {"role": "user", "content": user}],
            # strict JSON: the model can only return the fields of the schema
            "response_format": {"type": "json_schema", "json_schema": {
                "name": name, "strict": True,
                "schema": schema or {"type": "object",
                                     "properties": {"id": {"type": "integer"},
                                                    "lang": {"type": "string", "enum": ["en", "ur", "roman"]}},
                                     "required": ["id", "lang"], "additionalProperties": False}}},
            "reasoning_effort": "low",     # less thinking = fewer tokens (dropped below if the model does not accept it)
        }
        url = settings.GROQ_BASE_URL.rstrip("/") + "/chat/completions"
        n429 = 0
        for _ in range(8):
            for k in self.drop:
                body.pop(k, None)
            gap = self.min_gap - (time.time() - self.last_call)
            if gap > 0:
                time.sleep(gap)                                  # to stay under the rate limit
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
                if e.code == 429:                                # too many requests
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
                if e.code == 400 and "reasoning_effort" in body:     # the model does not accept this field
                    self.drop.add("reasoning_effort")
                    continue
                if e.code == 400 and "response_format" in body:      # the model does not accept strict JSON
                    self.drop.add("response_format")
                    continue
                self.last_error = f"HTTP {e.code}: {detail}"
                raise LLMError(self.last_error)
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
                self.last_error = f"{type(e).__name__}: {e}"
                raise LLMError(self.last_error)
        self.last_error = "failed even after many retries"
        raise LLMError(self.last_error)
