import time
import uuid
from dataclasses import dataclass
from typing import Any

from chromadb import PersistentClient
from chromadb.utils import embedding_functions

from app.utils.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, SEMANTIC_CACHE_CHROMA_DIR, SEMANTIC_CACHE_DISTANCE_THRESHOLD


@dataclass(frozen=True)
class SemanticCacheHit:
    response_text: str
    distance: float


class SemanticCacheService:
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY)
        self.collection: Any | None = None
        self.client = None
        if self.enabled:
            try:
                self.client = PersistentClient(path=str(SEMANTIC_CACHE_CHROMA_DIR))
                embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=OPENAI_API_KEY,
                    model_name=OPENAI_EMBEDDING_MODEL,
                )
                self.collection = self.client.get_or_create_collection(
                    name="semantic_llm_cache",
                    embedding_function=embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                self.client = None
                self.collection = None
                self.enabled = False

    def lookup(self, prompt_signature: str, route: str, model_name: str) -> SemanticCacheHit | None:
        if not self.enabled or self.collection is None or not prompt_signature.strip():
            return None
        try:
            result = self.collection.query(
                query_texts=[prompt_signature],
                n_results=1,
                where={
                    "$and": [
                        {"route": {"$eq": route}},
                        {"model_name": {"$eq": model_name}},
                    ]
                },
                include=["distances", "documents"],
            )
        except Exception:
            return None
        documents = (result.get("documents") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        if not documents or not distances:
            return None
        distance = float(distances[0])
        if distance > SEMANTIC_CACHE_DISTANCE_THRESHOLD:
            return None
        return SemanticCacheHit(response_text=str(documents[0]), distance=distance)

    def store(self, prompt_signature: str, route: str, model_name: str, response_text: str) -> None:
        if not self.enabled or self.collection is None or not prompt_signature.strip() or not response_text.strip():
            return
        try:
            self.collection.upsert(
                ids=[str(uuid.uuid4())],
                documents=[response_text],
                metadatas=[
                    {
                        "route": route,
                        "model_name": model_name,
                        "created_at": int(time.time()),
                        "signature_preview": prompt_signature[:300],
                    }
                ],
            )
        except Exception:
            return
