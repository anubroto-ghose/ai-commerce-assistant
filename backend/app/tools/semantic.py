import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class SimpleSemanticIndex:
    def __init__(self) -> None:
        self.doc_vectors: dict[str, Counter[str]] = {}

    def add(self, doc_id: str, text: str) -> None:
        self.doc_vectors[doc_id] = Counter(_tokenize(text))

    def score(self, query: str, doc_id: str) -> float:
        qv = Counter(_tokenize(query))
        dv = self.doc_vectors.get(doc_id)
        if not dv:
            return 0.0

        dot = sum(qv[token] * dv[token] for token in qv)
        q_norm = math.sqrt(sum(v * v for v in qv.values()))
        d_norm = math.sqrt(sum(v * v for v in dv.values()))
        if q_norm == 0 or d_norm == 0:
            return 0.0
        return dot / (q_norm * d_norm)
