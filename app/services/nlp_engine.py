# ===== nlp_engine.py : candidates from embeddings, then the LLM picks the right FAQ =====
import re
import numpy as np                                    # numpy = fast math
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from app.config import settings
from app.services.llm_matcher import LLMMatcher, LLMError

def detect_lang(question: str, llm_lang=None):
    """Language of the question: "ur" (Urdu script), "roman" (Roman Urdu) or "en" (English)."""
    letters = [c for c in question if c.isalpha()]
    arabic = [c for c in letters if "\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f"]
    if letters and len(arabic) / len(letters) > 0.3:       # Urdu script is detected by unicode, so it is reliable
        return "ur"
    if llm_lang == "roman":
        return "roman"
    return "en"                                             # "ur" from the LLM without Urdu letters => treat as English/other

def tokenize(text: str):
    return re.findall(r"\w+", text.lower())           # strip punctuation, split into words

class NLPEngine:
    def __init__(self, store):
        self.store = store
        self.llm = LLMMatcher()                       # the Groq part
        # load the model (downloaded from the internet the first time, then cached)
        self.model = SentenceTransformer(settings.MODEL_NAME)
        self.rebuild_index()                          # build vectors for all FAQ rows

    def _encode(self, texts, prefix):
        # normalize_embeddings=True => vectors have length 1, so dot product = cosine similarity
        return np.asarray(self.model.encode([prefix + t for t in texts],
                                            normalize_embeddings=True, show_progress_bar=False))

    def rebuild_index(self):
        # runs again whenever the FAQs change (a new one is added)
        self.texts = [f["question"] + " " + f["answer"] for f in self.store.faqs]
        self.emb = self._encode(self.texts, settings.PASSAGE_PREFIX)        # vectors of the FAQ rows
        self.bm25 = BM25Okapi([tokenize(t) for t in self.texts])            # keyword index
        self.groups = {}                                                    # answer -> all its paraphrase rows
        for f in self.store.faqs:
            self.groups.setdefault(f["answer"], []).append(f)

    def search(self, question: str, category: str = None, top_k: int = 3):
        faqs = self.store.faqs
        q = self._encode([question], settings.QUERY_PREFIX)[0]              # vector of the question
        sem = self.emb @ q                                                  # semantic score (cosine)
        w = settings.W_SEM
        if w < 1.0:                                                         # keyword score only if weight < 1
            kw = np.maximum(np.array(self.bm25.get_scores(tokenize(question))), 0)
            kw = kw / max(kw.max(), 1e-9)
            score = w * sem + (1 - w) * kw
        else:
            score = sem
        best = {}                                                           # answer -> (score, faq row)
        for i, f in enumerate(faqs):
            if category and f["category"] != category:                      # category filter
                continue
            a = f["answer"]
            if a not in best or score[i] > best[a][0]:                      # best of the paraphrases with the same answer
                best[a] = (float(score[i]), f)
        ranked = sorted(best.values(), key=lambda x: x[0], reverse=True)[:top_k]
        return [(f, s) for s, f in ranked]                                  # [(faq, score), ...]

    def answer(self, question: str, category: str = None):
        """Full decision: dict {matched, score, suggestions, source, lang}. matched=None => no answer found."""
        cands = self.search(question, category, top_k=max(settings.CANDIDATES, 3))
        if not cands:
            return {"matched": None, "score": 0.0, "suggestions": [], "source": "none", "lang": detect_lang(question)}
        if self.llm.enabled:
            try:
                # show the LLM the first (representative) question of each candidate group
                rep = lambda f: self.groups[f["answer"]][0]
                cl = [(int(rep(f)["id"]), f["category"], rep(f)["question"]) for f, _ in cands]
                cid, llm_lang = self.llm.choose(question, cl)
                lang = detect_lang(question, llm_lang)
                if cid == 0:                                                # LLM: no FAQ matches
                    return {"matched": None, "score": cands[0][1],
                            "suggestions": [f for f, _ in cands[:3]], "source": "llm", "lang": lang}
                for f, s in cands:
                    if int(rep(f)["id"]) == cid:
                        others = [x for x, _ in cands if x is not f][:2]
                        return {"matched": f, "score": s, "suggestions": others, "source": "llm", "lang": lang}
            except LLMError:
                pass                                                        # LLM failed => fall back to embeddings
        best, score = cands[0]
        matched = best if score >= settings.THRESHOLD else None
        return {"matched": matched, "score": score,
                "suggestions": [f for f, _ in cands[1:3]] if matched else [f for f, _ in cands[:3]],
                "source": "embedding", "lang": detect_lang(question)}
