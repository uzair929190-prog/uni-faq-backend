# ===== schemas.py : input/output format of the API (Pydantic validates it automatically) =====
from typing import List, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):            # the frontend sends this
    question: str                        # required: the user's question
    category: Optional[str] = None       # optional: may be empty (None)

class Suggestion(BaseModel):             # one item of "Did you mean this?"
    id: int
    question: str

class ChatResponse(BaseModel):           # the backend returns this
    answered: bool                       # True = answer found, False = fallback
    answer: str
    confidence: float                    # embedding similarity (0 to 1); not proof of the LLM's decision
    source: Optional[str] = None         # "llm" = chosen by the LLM, "embedding" = similarity only
    lang: Optional[str] = None           # language of the answer: "en", "ur" (Urdu script) or "roman"
    faq_id: Optional[int] = None
    matched_question: Optional[str] = None
    category: Optional[str] = None
    suggestions: List[Suggestion] = []   # empty list by default

class FeedbackRequest(BaseModel):        # thumbs up/down
    question: str
    faq_id: Optional[int] = None
    helpful: bool                        # True = up, False = down

class NewFAQ(BaseModel):                 # admin adds a new FAQ
    category: str
    question: str
    answer: str
