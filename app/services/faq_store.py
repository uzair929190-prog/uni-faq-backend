# ===== faq_store.py : FAQ data load/save karna =====
import pandas as pd
from app.config import settings

class FAQStore:
    def __init__(self):
        self.faqs = []           # shuru mein khali list
        self.load()              # object bante hi CSV load

    def load(self):
        df = pd.read_csv(settings.FAQ_CSV)         # CSV parho
        self.faqs = df.to_dict("records")          # har row = dict {id, category, question, answer}

    def add(self, category, question, answer):
        # naya id = sabse bada purana id + 1 (list khali ho to 0 + 1)
        new_id = max((int(f["id"]) for f in self.faqs), default=0) + 1
        row = {"id": new_id, "category": category, "question": question, "answer": answer}
        self.faqs.append(row)                                           # memory mein add
        pd.DataFrame(self.faqs).to_csv(settings.FAQ_CSV, index=False)   # CSV mein save (restart pe bhi rahe)
        return row

    def categories(self):
        return sorted({f["category"] for f in self.faqs})   # set = duplicate khatam, sorted = A-Z
