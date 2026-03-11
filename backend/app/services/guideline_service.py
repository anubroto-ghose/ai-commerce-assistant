import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from openai import OpenAI

from app.prompts.guideline_corpus import GUIDELINE_DOCUMENTS
from app.utils.config import FAISS_GUIDELINE_INDEX_PATH, FAISS_GUIDELINE_METADATA_PATH, OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL

try:
    import faiss
except Exception:  # pragma: no cover
    faiss = None


@dataclass(frozen=True)
class GuidelineMatch:
    document_id: str
    title: str
    text: str
    score: float


class GuidelineRetrievalService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.embedding_model = OPENAI_EMBEDDING_MODEL
        self.faiss_available = faiss is not None and self.client is not None
        self.documents = GUIDELINE_DOCUMENTS
        self.index = None
        self._metadata: list[dict] = []
        self._build_index()

    def _build_index(self) -> None:
        if not self.faiss_available or faiss is None:
            return
        try:
            texts = [self._embed_text(doc) for doc in self.documents]
            embeddings = self._embed_batch(texts)
            if embeddings.size == 0:
                return
            self.index = faiss.IndexFlatIP(embeddings.shape[1])
            self.index.add(embeddings)
            self._metadata = self.documents
            Path(FAISS_GUIDELINE_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(FAISS_GUIDELINE_INDEX_PATH))
            Path(FAISS_GUIDELINE_METADATA_PATH).write_text(json.dumps(self._metadata, indent=2), encoding="utf-8")
        except Exception:
            self.index = None
            self._metadata = []

    @staticmethod
    def _embed_text(doc: dict) -> str:
        return f"{doc['route']} {doc['title']} {doc['text']}"

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        if not texts or self.client is None:
            return np.array([], dtype=np.float32)
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        faiss.normalize_L2(vectors)
        return vectors

    def retrieve(self, query: str, route: str, top_k: int = 3) -> list[GuidelineMatch]:
        if not query.strip():
            return self._fallback(route, query, top_k)
        if self.faiss_available and self.index is not None and faiss is not None:
            query_vector = self._embed_batch([query])
            if query_vector.size:
                scores, indices = self.index.search(query_vector, min(top_k * 2, len(self.documents)))
                matches: list[GuidelineMatch] = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0 or idx >= len(self._metadata):
                        continue
                    doc = self._metadata[idx]
                    if doc["route"] not in {"all", route}:
                        continue
                    matches.append(
                        GuidelineMatch(
                            document_id=doc["id"],
                            title=doc["title"],
                            text=doc["text"],
                            score=float(score),
                        )
                    )
                    if len(matches) >= top_k:
                        break
                if matches:
                    return matches
        return self._fallback(route, query, top_k)

    def _fallback(self, route: str, query: str, top_k: int) -> list[GuidelineMatch]:
        lowered = query.lower()
        scored: list[GuidelineMatch] = []
        for doc in self.documents:
            if doc["route"] not in {"all", route}:
                continue
            doc_text = f"{doc['title']} {doc['text']}".lower()
            score = sum(1 for token in lowered.split() if token and token in doc_text)
            scored.append(
                GuidelineMatch(
                    document_id=doc["id"],
                    title=doc["title"],
                    text=doc["text"],
                    score=float(score),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]
