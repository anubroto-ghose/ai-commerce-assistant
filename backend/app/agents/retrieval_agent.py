from app.models.product import ProductRecord
from app.services.retrieval_service import RetrievalService


class RetrievalAgent:
    def __init__(self, retrieval_service: RetrievalService) -> None:
        self.retrieval_service = retrieval_service

    def retrieve(self, query: str, products: list[ProductRecord]) -> list[tuple[ProductRecord, float]]:
        return self.retrieval_service.semantic_rank(query, products)
