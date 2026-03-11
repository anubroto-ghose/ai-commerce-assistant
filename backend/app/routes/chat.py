from fastapi import APIRouter, HTTPException

from app.schemas.api import ChatRequest, ChatResponse
from app.services.container import get_container
from app.services.serializers import to_product_result
from app.utils.config import POOR_RATING_THRESHOLD

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def product_chat(payload: ChatRequest) -> ChatResponse:
    container = get_container()
    tracing = container.get("tracing")
    if tracing is None:
        return _product_chat_impl(container, payload)
    with tracing.span(
        name="api.chat",
        run_type="chain",
        inputs={"product_id": payload.product_id, "message": payload.message[:300]},
        tags=["api", "chat"],
    ) as run_id:
        response = _product_chat_impl(container, payload)
        tracing.end_span(
            run_id,
            outputs={
                "needs_product_id": response.needs_product_id,
                "product_id": response.product_id,
                "workflow_summary": response.workflow_summary,
            },
        )
        return response


def _product_chat_impl(container: dict, payload: ChatRequest) -> ChatResponse:
    session = container["sessions"].ensure_session(payload.session_id)
    guardrails = container["guardrails"]
    validation = guardrails.validate_user_input(payload.message, route="chat")
    container["sessions"].append_message(session.session_id, "user", payload.message)
    if validation.blocked:
        safe_text = guardrails.sanitize_blocked_response(validation.category)
        container["sessions"].append_message(session.session_id, "assistant", safe_text)
        return ChatResponse(session_id=session.session_id, needs_product_id=False, response=safe_text)

    product_id = payload.product_id
    if not product_id:
        msg = "Please share a Product ID so I can analyze reviews, rating, availability, and ingredients."
        container["sessions"].append_message(session.session_id, "assistant", msg)
        return ChatResponse(
            session_id=session.session_id,
            needs_product_id=True,
            response=msg,
        )

    product = container["repo"].get_by_product_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product ID not found")

    summary = container["orchestrator"].analyze_product(product)
    history = container["sessions"].get_recent_messages(session.session_id, limit=12)
    llm_result = container["llm"].answer_product_chat(
        user_message=payload.message,
        product=product,
        summary=summary,
        session_messages=history,
        session_id=session.session_id,
    )
    message = llm_result.text
    message = guardrails.redact_sensitive_output(message)
    output_validation = guardrails.validate_model_output(message)
    if output_validation.blocked:
        message = guardrails.sanitize_blocked_response(output_validation.category)

    alternatives = []
    if product.rating < POOR_RATING_THRESHOLD:
        candidates = container["orchestrator"].alternatives(product, container["products"], limit=3)
        alternatives = [to_product_result(p) for p in candidates]
        if alternatives:
            message += "\nThis product has mixed/low ratings. Here are better-rated alternatives in the same category."
    container["sessions"].append_message(session.session_id, "assistant", message)

    return ChatResponse(
        session_id=session.session_id,
        needs_product_id=False,
        product_id=product.product_id,
        response=message,
        product_summary=summary,
        alternatives=alternatives,
        workflow_summary=llm_result.workflow_summary,
    )
