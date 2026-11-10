# ===== routes.py : all API endpoints (URLs) =====
from fastapi import APIRouter, Header, HTTPException, Request
from app.config import settings
from app.schemas import ChatRequest, ChatResponse, FeedbackRequest, NewFAQ, Suggestion
from app.utils.logger import log_jsonl

router = APIRouter()      # group of endpoints

NOT_FOUND = {                                            # "no answer" message in every language
    "en": "Sorry, I couldn't find an exact answer. Did you mean one of these?",
    "ur": "معذرت، مجھے اس کا درست جواب نہیں ملا۔ کیا آپ ان میں سے کوئی پوچھنا چاہتے تھے؟",
    "roman": "Maazrat, mujhe iska sahi jawab nahi mila. Kya aap inmein se koi poochna chahte the?",
}

def _sug(rows):
    return [Suggestion(id=int(f["id"]), question=f["question"]) for f in rows]

@router.get("/health")                                   # GET /health : is the server alive?
def health(request: Request):
    return {"status": "ok", "faqs": len(request.app.state.store.faqs),
            "llm": request.app.state.engine.llm.enabled}

@router.get("/categories")                               # GET /categories : for sidebar / chips
def categories(request: Request):
    return request.app.state.store.categories()

@router.post("/chat", response_model=ChatResponse)       # POST /chat : main endpoint
def chat(req: ChatRequest, request: Request):
    r = request.app.state.engine.answer(req.question, req.category)
    if r["source"] == "none":
        raise HTTPException(404, "No FAQs found for this category")
    score = round(r["score"], 3)
    m = r["matched"]
    lang = r.get("lang", "en")

    if m is None:                       # no answer found: do not guess
        log_jsonl("unanswered.jsonl", {"question": req.question, "score": score, "source": r["source"]})
        return ChatResponse(
            answered=False, confidence=score, source=r["source"], lang=lang,
            answer=NOT_FOUND.get(lang, NOT_FOUND["en"]),
            suggestions=_sug(r["suggestions"]))

    return ChatResponse(
        answered=True, confidence=score, source=r["source"], lang=lang,
        answer=request.app.state.store.answer_in(m, lang),
        faq_id=int(m["id"]), matched_question=m["question"], category=m["category"],
        suggestions=_sug(r["suggestions"]))

@router.post("/feedback")                                # POST /feedback : thumbs up/down
def feedback(req: FeedbackRequest):
    log_jsonl("feedback.jsonl", req.model_dump())
    return {"saved": True}

@router.post("/admin/faq")                               # POST /admin/faq : admin only
def add_faq(new: NewFAQ, request: Request, x_api_key: str = Header(None)):
    if x_api_key != settings.ADMIN_KEY:                  # the header must carry the right key
        raise HTTPException(401, "Invalid admin key")
    row = request.app.state.store.add(new.category, new.question, new.answer)
    request.app.state.engine.rebuild_index()             # so the new FAQ shows up in search
    return {"added": True, "id": row["id"]}
