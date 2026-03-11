from app.models.product import ProductRecord


class RecommendationAgent:
    def recommend_alternatives(
        self,
        source: ProductRecord,
        pool: list[ProductRecord],
        limit: int = 3,
    ) -> list[ProductRecord]:
        candidates = [
            p
            for p in pool
            if p.product_id != source.product_id
            and p.category_name == source.category_name
            and p.rating >= max(4.0, source.rating)
        ]
        candidates.sort(key=lambda p: (p.rating, p.review_count), reverse=True)
        return candidates[:limit]
