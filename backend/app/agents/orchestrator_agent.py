from app.agents.product_analysis_agent import ProductAnalysisAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.models.product import ProductRecord
from app.services.tracing_service import TracingService
from app.tools.query_parser import parse_search_intent


class OrchestratorAgent:
    def __init__(
        self,
        retrieval_agent: RetrievalAgent,
        analysis_agent: ProductAnalysisAgent,
        recommendation_agent: RecommendationAgent,
        tracing_service: TracingService | None = None,
    ) -> None:
        self.retrieval_agent = retrieval_agent
        self.analysis_agent = analysis_agent
        self.recommendation_agent = recommendation_agent
        self.tracing_service = tracing_service

    def search(self, query: str, products: list[ProductRecord], limit: int) -> tuple[list[ProductRecord], dict]:
        if self.tracing_service is None:
            return self._search_impl(query=query, products=products, limit=limit)
        with self.tracing_service.span(
            name="orchestrator.search",
            run_type="chain",
            inputs={"query": query, "limit": limit, "product_count": len(products)},
            tags=["agent", "search"],
        ) as run_id:
            filtered, interpreted = self._search_impl(query=query, products=products, limit=limit)
            self.tracing_service.end_span(
                run_id,
                outputs={"result_count": len(filtered), "interpreted_filters": interpreted},
            )
            return filtered, interpreted

    def analyze_product(self, product: ProductRecord) -> dict:
        if self.tracing_service is None:
            return self.analysis_agent.summarize_product(product)
        with self.tracing_service.span(
            name="orchestrator.analyze_product",
            run_type="chain",
            inputs={"product_id": product.product_id},
            tags=["agent", "analysis"],
        ) as run_id:
            summary = self.analysis_agent.summarize_product(product)
            self.tracing_service.end_span(
                run_id,
                outputs={"sentiment": summary.get("sentiment"), "review_count": summary.get("review_count")},
            )
            return summary

    def alternatives(self, product: ProductRecord, pool: list[ProductRecord], limit: int = 3) -> list[ProductRecord]:
        if self.tracing_service is None:
            return self.recommendation_agent.recommend_alternatives(product=product, pool=pool, limit=limit)
        with self.tracing_service.span(
            name="orchestrator.alternatives",
            run_type="chain",
            inputs={"product_id": product.product_id, "limit": limit, "pool_size": len(pool)},
            tags=["agent", "recommendation"],
        ) as run_id:
            results = self.recommendation_agent.recommend_alternatives(product=product, pool=pool, limit=limit)
            self.tracing_service.end_span(run_id, outputs={"alternative_count": len(results)})
            return results

    def _search_impl(self, query: str, products: list[ProductRecord], limit: int) -> tuple[list[ProductRecord], dict]:
        intent = parse_search_intent(query)
        ranked = self.retrieval_agent.retrieve(query, products)

        candidate_cap = max(limit * 8, 30)
        filtered = []
        for product, score in ranked:
            if intent.max_price is not None and product.final_price > intent.max_price:
                continue
            if intent.min_rating is not None and product.rating < intent.min_rating:
                continue
            if intent.inferred_category:
                haystack = f"{product.category_name} {product.root_category_name} {product.description}".lower()
                if intent.inferred_category not in haystack:
                    continue
            if score <= 0 and not (intent.max_price or intent.min_rating or intent.inferred_category):
                continue
            filtered.append(product)
            if len(filtered) >= candidate_cap:
                break

        return filtered, {
            "max_price": intent.max_price,
            "min_rating": intent.min_rating,
            "category": intent.inferred_category,
        }
