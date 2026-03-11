from fastapi import APIRouter, HTTPException

from app.schemas.api import SearchRequest, SearchResponse
from app.services.container import get_container
from app.services.serializers import to_product_result

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def product_search(payload: SearchRequest) -> SearchResponse:
    container = get_container()
    tracing = container.get("tracing")
    if tracing is None:
        return _product_search_impl(container, payload)
    with tracing.span(
        name="api.search",
        run_type="chain",
        inputs={"query": payload.query, "limit": payload.limit},
        tags=["api", "search"],
    ) as run_id:
        response = _product_search_impl(container, payload)
        tracing.end_span(
            run_id,
            outputs={
                "total_results": response.total_results,
                "suggested_search": response.suggested_search,
                "detected_language": response.detected_language,
            },
        )
        return response


def _product_search_impl(container: dict, payload: SearchRequest) -> SearchResponse:
    guardrails = container["guardrails"]
    validation = guardrails.validate_user_input(payload.query, route="search")
    if validation.blocked:
        raise HTTPException(status_code=400, detail=validation.reason)

    prep = container["llm"].prepare_search_query(payload.query)

    candidates, interpreted = container["orchestrator"].search(
        query=prep.retrieval_query,
        products=container["products"],
        limit=payload.limit,
    )
    reranked = container["llm"].rerank_and_filter_search_results(
        query=payload.query,
        candidates=candidates,
        final_limit=payload.limit,
    )
    final_suggestion = reranked.suggested_query or prep.suggested_query
    final_language = reranked.language or prep.language
    serialized = [to_product_result(p) for p in reranked.products]
    return SearchResponse(
        query=payload.query,
        suggested_search=final_suggestion,
        detected_language=final_language,
        interpreted_filters=interpreted,
        total_results=len(serialized),
        products=serialized,
        workflow_summary=f"Prepare: {prep.workflow_summary} Rerank: {reranked.workflow_summary}",
    )
