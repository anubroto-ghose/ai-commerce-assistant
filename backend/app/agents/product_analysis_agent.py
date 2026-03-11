from collections import Counter

from app.models.product import ProductRecord


class ProductAnalysisAgent:
    def summarize_product(self, product: ProductRecord) -> dict:
        reviews = product.customer_reviews or []
        ratings = [int(float(r.get("rating", 0))) for r in reviews if r.get("rating") is not None]

        positive = [r.get("review", "") for r in reviews if float(r.get("rating", 0) or 0) >= 4][:3]
        negative = [r.get("review", "") for r in reviews if float(r.get("rating", 0) or 0) <= 2][:3]

        sentiment = "mixed"
        if ratings:
            avg = sum(ratings) / len(ratings)
            if avg >= 4:
                sentiment = "mostly positive"
            elif avg <= 2.5:
                sentiment = "mostly negative"

        top_terms = Counter(
            token
            for text in positive + negative
            for token in str(text).lower().split()
            if len(token) > 4
        ).most_common(5)

        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "rating": product.rating,
            "review_count": product.review_count,
            "sentiment": sentiment,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "common_themes": [term for term, _ in top_terms],
            "available_for_delivery": product.available_for_delivery,
            "available_for_pickup": product.available_for_pickup,
            "ingredients": product.ingredients,
        }
