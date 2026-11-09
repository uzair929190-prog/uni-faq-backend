# ===== main.py : app ka entry point =====
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router
from app.services.faq_store import FAQStore
from app.services.nlp_engine import NLPEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ye hissa server start hote waqt EK dafa chalta hai
    store = FAQStore()                    # CSV se data load
    app.state.store = store               # routes isko request.app.state se use karti hain
    app.state.engine = NLPEngine(store)   # model load + index (10-20 sec lagte hain)
    yield                                 # ab server requests ke liye tayyar

app = FastAPI(title="University FAQ API", version="1.0", lifespan=lifespan)

# CORS = browser ki security. Iske baghair Lovable ki website backend se baat nahi kar sakti.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,   # .env wali list
    # regex = Lovable ke saare domains (preview + published) allow
    allow_origin_regex=r"https://.*\.(lovable\.app|lovableproject\.com|lovable\.dev)",
    allow_methods=["*"],                      # GET, POST, OPTIONS sab
    allow_headers=["*"],                      # saare headers
)

app.include_router(router)                    # routes.py ke endpoints jod do
