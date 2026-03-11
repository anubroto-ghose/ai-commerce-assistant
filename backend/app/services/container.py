from functools import lru_cache

from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.product_analysis_agent import ProductAnalysisAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.guardrails.safety import SafetyGuardrails
from app.llm.service import LLMService
from app.services.db_service import ProductRepository
from app.services.guideline_service import GuidelineRetrievalService
from app.services.metrics_service import MetricsService
from app.services.privacy_service import PrivacyService
from app.services.prompt_optimization_service import PromptOptimizationService
from app.services.retrieval_service import RetrievalService
from app.services.semantic_cache_service import SemanticCacheService
from app.services.session_service import InMemorySessionService
from app.services.tracing_service import TracingService


@lru_cache(maxsize=1)
def get_container() -> dict:
    repo = ProductRepository()
    products = repo.all_products()

    retrieval_service = RetrievalService()
    retrieval_service.build_index(products)
    metrics = MetricsService()
    privacy = PrivacyService()
    guideline_retrieval = GuidelineRetrievalService()
    prompt_optimization = PromptOptimizationService()
    semantic_cache = SemanticCacheService()
    tracing = TracingService()

    orchestrator = OrchestratorAgent(
        retrieval_agent=RetrievalAgent(retrieval_service),
        analysis_agent=ProductAnalysisAgent(),
        recommendation_agent=RecommendationAgent(),
        tracing_service=tracing,
    )

    return {
        "repo": repo,
        "products": products,
        "orchestrator": orchestrator,
        "guardrails": SafetyGuardrails(),
        "llm": LLMService(
            privacy_service=privacy,
            metrics_service=metrics,
            guideline_service=guideline_retrieval,
            prompt_optimization_service=prompt_optimization,
            semantic_cache_service=semantic_cache,
            tracing_service=tracing,
        ),
        "metrics": metrics,
        "tracing": tracing,
        "sessions": InMemorySessionService(ttl_seconds=300),
    }
