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
