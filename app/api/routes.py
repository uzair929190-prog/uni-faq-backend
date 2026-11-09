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
