import os
from pathlib import Path

from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = WORKSPACE_ROOT / "backend"
ENV_PATH = BACKEND_ROOT / ".env"
load_dotenv(ENV_PATH, override=False)

DATA_DB_PATH = WORKSPACE_ROOT / "data" / "walmart_products.db"
METRICS_DB_PATH = WORKSPACE_ROOT / "data" / "system_metrics.db"

DEFAULT_CHROMA_DIR = WORKSPACE_ROOT / "data" / "chroma_store"
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIRECTORY", str(DEFAULT_CHROMA_DIR))).resolve()
SEMANTIC_CACHE_CHROMA_DIR = Path(
    os.getenv("SEMANTIC_CACHE_CHROMA_DIR", str(WORKSPACE_ROOT / "data" / "semantic_cache_store"))
).resolve()
SEMANTIC_CACHE_DISTANCE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_DISTANCE_THRESHOLD", "0.12"))
FAISS_GUIDELINE_INDEX_PATH = WORKSPACE_ROOT / "data" / "guideline_faiss.index"
FAISS_GUIDELINE_METADATA_PATH = WORKSPACE_ROOT / "data" / "guideline_faiss_metadata.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"')
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
LLMLINGUA_ENABLED = os.getenv("LLMLINGUA_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "").strip().strip('"')
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").strip()
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "genai-ecommerce-assistant").strip()
LANGSMITH_TRACING_ENABLED = os.getenv("LANGSMITH_TRACING", "false").strip().lower() in {"1", "true", "yes", "on"}

DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 15
POOR_RATING_THRESHOLD = 3.5
