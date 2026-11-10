# ===== faq_store.py : load / save the FAQ data =====
import json
import pandas as pd
from app.config import settings

class FAQStore:
    def __init__(self):
        self.faqs = []           # empty list at first
        self.load()              # load the CSV as soon as the object is created

    def load(self):
        df = pd.read_csv(settings.FAQ_CSV)         # read the CSV
        self.faqs = df.to_dict("records")          # each row = dict {id, category, question, answer}
        self.tr = {}                               # English answer -> {"ur": ..., "roman": ...}
        path = settings.FAQ_CSV.parent / "translations.json"
        if path.exists():
            try:
                self.tr = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.tr = {}                       # broken file => just answer in English

    def answer_in(self, faq, lang):
        """Answer text in the requested language ("ur" / "roman"); English if there is no translation."""
        t = self.tr.get(faq["answer"])
        if lang in ("ur", "roman") and t and t.get(lang):
            return t[lang]
        return faq["answer"]

    def add(self, category, question, answer):
        # new id = largest old id + 1 (0 + 1 if the list is empty)
        new_id = max((int(f["id"]) for f in self.faqs), default=0) + 1
        row = {"id": new_id, "category": category, "question": question, "answer": answer}
        self.faqs.append(row)                                           # add in memory
        pd.DataFrame(self.faqs).to_csv(settings.FAQ_CSV, index=False)   # save to CSV (survives restart)
        return row

    def categories(self):
        return sorted({f["category"] for f in self.faqs})   # set = remove duplicates, sorted = A-Z
