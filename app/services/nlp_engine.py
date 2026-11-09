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
