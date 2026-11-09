# ===== config.py : saari settings ek jagah (baqi files yahan se import karti hain) =====
import os                                    # os = environment variables parhne ke liye
from pathlib import Path                     # Path = file/folder ke raaste handle karna
from dotenv import load_dotenv               # .env file load karne wali library

# __file__ = ye file; .parent.parent = do folder upar = backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")               # .env ke variables memory mein aa gaye

class Settings:
    # ---- embeddings (candidates nikalne ke liye) ----
    MODEL_NAME = os.getenv("MODEL_NAME", "intfloat/multilingual-e5-small")
    QUERY_PREFIX = os.getenv("QUERY_PREFIX", "query: ")        # e5 ko ye prefixes chahiye
    PASSAGE_PREFIX = os.getenv("PASSAGE_PREFIX", "passage: ")
    THRESHOLD = float(os.getenv("THRESHOLD", 0.0))             # sirf tab kaam aata hai jab LLM band ho
    W_SEM = float(os.getenv("W_SEM", 1.0))                     # 1.0 = sirf meaning
    # ---- Groq LLM (sahi FAQ chunne ke liye) ----
    USE_LLM = os.getenv("USE_LLM", "1") == "1"                 # "0" likho to LLM band
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")               # key sirf .env mein, code mein kabhi nahi
    GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    CANDIDATES = int(os.getenv("CANDIDATES", 25))              # embeddings ke top-N FAQs LLM ko jate hain
    # ---- baqi ----
    ADMIN_KEY = os.getenv("ADMIN_KEY", "changeme")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    FAQ_CSV = BASE_DIR / "data" / "faqs.csv"
    LOG_DIR = BASE_DIR / "logs"

settings = Settings()    # ek hi object poori app mein use hoga
