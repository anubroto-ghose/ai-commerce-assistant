import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.models.product import ProductRecord
from app.prompts.system_prompts import CHAT_SYSTEM_PROMPT, SEARCH_SYSTEM_PROMPT
from app.services.guideline_service import GuidelineRetrievalService
from app.services.metrics_service import MetricsService
from app.services.privacy_service import PrivacyService
from app.services.prompt_optimization_service import CompressionResult, PromptOptimizationService
from app.services.semantic_cache_service import SemanticCacheService
from app.services.tracing_service import TracingService
from app.utils.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL


@dataclass(frozen=True)
class PromptExecutionResult:
    text: str
    workflow_summary: str


@dataclass(frozen=True)
class SearchPreparationResult:
    retrieval_query: str
    suggested_query: str | None
    language: str | None
    workflow_summary: str


@dataclass(frozen=True)
class SearchRerankResult:
    products: list[ProductRecord]
    suggested_query: str | None
    language: str | None
    workflow_summary: str


class LLMService:
    def __init__(
        self,
        *,
        privacy_service: PrivacyService,
        metrics_service: MetricsService,
        guideline_service: GuidelineRetrievalService,
        prompt_optimization_service: PromptOptimizationService,
        semantic_cache_service: SemanticCacheService,
        tracing_service: TracingService | None = None,
    ) -> None:
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.chat_model = OPENAI_CHAT_MODEL
        self.privacy_service = privacy_service
        self.metrics_service = metrics_service
        self.guideline_service = guideline_service
        self.prompt_optimization_service = prompt_optimization_service
        self.semantic_cache_service = semantic_cache_service
        self.tracing_service = tracing_service

    def summarize_product_analysis(self, product: ProductRecord, summary: dict) -> str:
        positives = summary.get("positive_feedback") or []
        negatives = summary.get("negative_feedback") or []
        sentiment = summary.get("sentiment", "mixed")

        lines = [
            f"{product.product_name} has a {sentiment} reception.",
            f"Current rating is {product.rating:.1f} from {product.review_count} reviews.",
            f"Delivery: {'Yes' if product.available_for_delivery else 'No'}, Pickup: {'Yes' if product.available_for_pickup else 'No'}.",
        ]
        if positives:
            lines.append("People like: " + " | ".join(str(x)[:140] for x in positives[:2]))
        if negatives:
            lines.append("Concerns: " + " | ".join(str(x)[:140] for x in negatives[:2]))
        if product.ingredients:
            lines.append("Ingredients: " + product.ingredients[:220])
        fallback = "\n".join(lines)

        prompt = (
            "Summarize quality using only given facts. Return concise bullets for strengths, concerns, and verdict.\n"
            f"Product: {product.product_name}\n"
            f"Rating: {product.rating}, Review count: {product.review_count}\n"
            f"Sentiment: {sentiment}\n"
            f"Positive feedback snippets: {positives[:3]}\n"
            f"Negative feedback snippets: {negatives[:3]}\n"
            f"Availability delivery/pickup: {product.available_for_delivery}/{product.available_for_pickup}\n"
            f"Ingredients: {product.ingredients[:600]}"
        )
        result = self._run_secure_prompt(
            route="analysis_summary",
            user_input=prompt,
            system_prompt=CHAT_SYSTEM_PROMPT,
            additional_context="",
            fallback_text=fallback,
            enable_semantic_cache=False,
        )
        return result.text

    def answer_product_chat(
        self,
        user_message: str,
        product: ProductRecord,
        summary: dict,
        session_messages: list[dict],
        session_id: str | None = None,
    ) -> PromptExecutionResult:
        fallback = self._fallback_chat_reply(user_message=user_message, product=product, summary=summary)

        compact_history = []
        for msg in session_messages[-10:]:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            content = str(msg.get("content") or "")[:300]
            compact_history.append({"role": role, "content": content})

        additional_context = (
            "Product facts:\n"
            f"- Product name: {product.product_name}\n"
            f"- Product ID: {product.product_id}\n"
            f"- Price: {product.currency} {product.final_price:.2f}\n"
            f"- Rating: {product.rating} ({product.review_count} reviews)\n"
            f"- Delivery: {product.available_for_delivery}, Pickup: {product.available_for_pickup}\n"
            f"- Ingredients: {product.ingredients[:500]}\n"
            f"- Analysis summary: {json.dumps(summary, ensure_ascii=False)[:1200]}\n"
            f"- Conversation history: {json.dumps(compact_history, ensure_ascii=False)}"
        )
        prompt = (
            "Answer the latest product question naturally.\n"
            "Rules:\n"
            "1) Use only given product facts.\n"
            "2) Keep response concise unless the user asks for detail.\n"
            "3) Maintain continuity with prior turns.\n"
            f"Latest user message: {user_message}"
        )
        return self._run_secure_prompt(
            route="chat",
            user_input=prompt,
            system_prompt=CHAT_SYSTEM_PROMPT,
            additional_context=additional_context,
            fallback_text=fallback,
            session_id=session_id,
        )

    def rerank_and_filter_search_results(
        self,
        query: str,
        candidates: list[ProductRecord],
        final_limit: int,
    ) -> SearchRerankResult:
        heuristic_products, heuristic_suggested, heuristic_language = self._heuristic_rerank(
            query=query,
            candidates=candidates,
            final_limit=final_limit,
        )
        compact_candidates = []
        for product in candidates[:80]:
            compact_candidates.append(
                {
                    "id": product.product_id,
                    "name": product.product_name[:140],
                    "category": product.category_name[:70],
                    "root_category": product.root_category_name[:70],
                    "description": product.description[:220],
                }
            )

        prompt = (
            "Return JSON with keys: language, suggested_query, selected_ids, include_terms, exclude_terms.\n"
            "Select only truly relevant product IDs and preserve user intent.\n"
            f"Maximum selected_ids length: {final_limit}.\n"
            f"Query: {query}\n"
            f"Candidates: {json.dumps(compact_candidates, ensure_ascii=False)}"
        )
        result = self._run_secure_prompt(
            route="search_rerank",
            user_input=prompt,
            system_prompt=SEARCH_SYSTEM_PROMPT,
            additional_context="",
            fallback_text="",
        )
        if not result.text.strip():
            return SearchRerankResult(heuristic_products, heuristic_suggested, heuristic_language, result.workflow_summary)

        try:
            payload = self._parse_json(result.text)
            selected_ids = payload.get("selected_ids") or []
            by_id = {product.product_id: product for product in candidates}
            selected = [by_id[pid] for pid in selected_ids if pid in by_id][:final_limit]
            include_terms = self._normalize_term_list(payload.get("include_terms"))
            exclude_terms = self._normalize_term_list(payload.get("exclude_terms"))
            selected = self._filter_by_terms(selected, include_terms, exclude_terms)
            if not selected:
                return SearchRerankResult(
                    heuristic_products,
                    heuristic_suggested,
                    heuristic_language,
                    result.workflow_summary,
                )
            suggested = payload.get("suggested_query")
            language = payload.get("language")
            if suggested and suggested.strip().lower() == query.strip().lower():
                suggested = None
            return SearchRerankResult(selected, suggested, language, result.workflow_summary)
        except Exception:
            return SearchRerankResult(heuristic_products, heuristic_suggested, heuristic_language, result.workflow_summary)

    def prepare_search_query(self, query: str) -> SearchPreparationResult:
        fallback_language = self._detect_language(self._normalize_query(query))
        fallback_suggestion = self._spelling_suggestion(query)
        fallback_retrieval = f"{query} {fallback_suggestion}".strip() if fallback_suggestion else query

        prompt = (
            "Return JSON with keys: language, suggested_query, retrieval_query.\n"
            "Keep user intent exactly. Enrich short or non-English queries with concise retrieval terms.\n"
            f"Query: {query}"
        )
        result = self._run_secure_prompt(
            route="search_prepare",
            user_input=prompt,
            system_prompt=SEARCH_SYSTEM_PROMPT,
            additional_context="",
            fallback_text="",
        )
        try:
            payload = self._parse_json(result.text)
            language = payload.get("language") or fallback_language
            suggested = payload.get("suggested_query") or fallback_suggestion
            retrieval_query = (payload.get("retrieval_query") or query).strip()
            if suggested and suggested.strip().lower() == query.strip().lower():
                suggested = None
            return SearchPreparationResult(retrieval_query or fallback_retrieval, suggested, language, result.workflow_summary)
        except Exception:
            return SearchPreparationResult(fallback_retrieval, fallback_suggestion, fallback_language, result.workflow_summary)

    def _run_secure_prompt(
        self,
        *,
        route: str,
        user_input: str,
        system_prompt: str,
        additional_context: str,
        fallback_text: str,
        session_id: str | None = None,
        enable_semantic_cache: bool = True,
    ) -> PromptExecutionResult:
        trace_run_id = None
        if self.tracing_service is not None:
            trace_run_id = self.tracing_service.start_span(
                name=f"llm.{route}",
                run_type="llm",
                inputs={
                    "route": route,
                    "model_name": self.chat_model,
                    "user_input_preview": user_input[:300],
                    "session_id": session_id,
                    "semantic_cache_enabled": enable_semantic_cache,
                },
                tags=["llm", route],
            )

        route_group = "search" if route.startswith("search") else "chat"
        anonymized = self.privacy_service.anonymize_text(user_input)
        guidelines = self.guideline_service.retrieve(anonymized.anonymized_text, route=route_group)
        guideline_text = "\n".join(f"{item.title}: {item.text}" for item in guidelines)
        compression = self.prompt_optimization_service.compress(system_prompt=system_prompt, retrieved_context=guideline_text)
        final_prompt = "\n\n".join(
            part
            for part in [
                f"Compressed instructions:\n{compression.compressed_text}",
                additional_context.strip(),
                f"User input after PII anonymization:\n{anonymized.anonymized_text}",
            ]
            if part.strip()
        )
        workflow_summary = self._workflow_summary(
            pii_entities=anonymized.entity_types,
            guideline_ids=[item.document_id for item in guidelines],
            compression=compression,
            cache_hit=False,
        )
        model_name = self.chat_model

        cached = None
        if enable_semantic_cache:
            cached = self.semantic_cache_service.lookup(final_prompt, route=route, model_name=model_name)
        if cached is not None:
            workflow_summary = self._workflow_summary(
                pii_entities=anonymized.entity_types,
                guideline_ids=[item.document_id for item in guidelines],
                compression=compression,
                cache_hit=True,
            )
            usage_id = self.metrics_service.log_llm_usage(
                route=route,
                model_name=model_name,
                input_tokens=0,
                cached_input_tokens=0,
                output_tokens=0,
                cache_hit=True,
                pii_entities_count=len(anonymized.entity_types),
                compressed_chars_before=compression.original_chars,
                compressed_chars_after=compression.compressed_chars,
                workflow_summary=workflow_summary,
            )
            self.metrics_service.log_request_trace(
                route=route,
                session_id=session_id,
                model_name=model_name,
                input_preview=user_input[:200],
                anonymized_preview=anonymized.anonymized_text[:200],
                pii_entities=anonymized.entity_types,
                guideline_ids=[item.document_id for item in guidelines],
                cache_hit=True,
                compression_ratio=self._compression_ratio(compression),
                llm_usage_id=usage_id,
                response_preview=cached.response_text[:200],
            )
            if self.tracing_service is not None:
                self.tracing_service.end_span(
                    trace_run_id,
                    outputs={
                        "result_type": "semantic_cache_hit",
                        "cache_hit": True,
                        "model_name": model_name,
                        "workflow_summary": workflow_summary,
                        "pii_entities": anonymized.entity_types,
                        "guideline_ids": [item.document_id for item in guidelines],
                        "compression_ratio": self._compression_ratio(compression),
                        "response_preview": cached.response_text[:300],
                    },
                )
            return PromptExecutionResult(text=cached.response_text, workflow_summary=workflow_summary)

        if not self.client:
            self.metrics_service.log_request_trace(
                route=route,
                session_id=session_id,
                model_name=model_name,
                input_preview=user_input[:200],
                anonymized_preview=anonymized.anonymized_text[:200],
                pii_entities=anonymized.entity_types,
                guideline_ids=[item.document_id for item in guidelines],
                cache_hit=False,
                compression_ratio=self._compression_ratio(compression),
                llm_usage_id=None,
                response_preview=fallback_text[:200],
            )
            if self.tracing_service is not None:
                self.tracing_service.end_span(
                    trace_run_id,
                    outputs={
                        "result_type": "fallback_no_openai_client",
                        "cache_hit": False,
                        "model_name": model_name,
                        "workflow_summary": workflow_summary,
                        "pii_entities": anonymized.entity_types,
                        "guideline_ids": [item.document_id for item in guidelines],
                        "compression_ratio": self._compression_ratio(compression),
                        "response_preview": fallback_text[:300],
                    },
                )
            return PromptExecutionResult(text=fallback_text, workflow_summary=workflow_summary)

        try:
            response = self.client.responses.create(model=model_name, input=final_prompt)
            text = (response.output_text or "").strip() or fallback_text
            if enable_semantic_cache and text.strip():
                self.semantic_cache_service.store(final_prompt, route=route, model_name=model_name, response_text=text)
            usage = getattr(response, "usage", None)
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            input_details = getattr(usage, "input_tokens_details", None)
            cached_input_tokens = int(getattr(input_details, "cached_tokens", 0) or 0)
            usage_id = self.metrics_service.log_llm_usage(
                route=route,
                model_name=model_name,
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
                cache_hit=False,
                pii_entities_count=len(anonymized.entity_types),
                compressed_chars_before=compression.original_chars,
                compressed_chars_after=compression.compressed_chars,
                workflow_summary=workflow_summary,
            )
            self.metrics_service.log_request_trace(
                route=route,
                session_id=session_id,
                model_name=model_name,
                input_preview=user_input[:200],
                anonymized_preview=anonymized.anonymized_text[:200],
                pii_entities=anonymized.entity_types,
                guideline_ids=[item.document_id for item in guidelines],
                cache_hit=False,
                compression_ratio=self._compression_ratio(compression),
                llm_usage_id=usage_id,
                response_preview=text[:200],
            )
            usage_cost = self.metrics_service.calculate_cost(
                model_name=model_name,
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
            )
            if self.tracing_service is not None:
                self.tracing_service.end_span(
                    trace_run_id,
                    outputs={
                        "result_type": "llm_response",
                        "cache_hit": False,
                        "model_name": model_name,
                        "workflow_summary": workflow_summary,
                        "usage": {
                            "input_tokens": input_tokens,
                            "cached_input_tokens": cached_input_tokens,
                            "output_tokens": output_tokens,
                            "cost_usd": usage_cost,
                            "metrics_usage_id": usage_id,
                        },
                        "pii_entities": anonymized.entity_types,
                        "guideline_ids": [item.document_id for item in guidelines],
                        "compression_ratio": self._compression_ratio(compression),
                        "response_preview": text[:300],
                    },
                )
            return PromptExecutionResult(text=text, workflow_summary=workflow_summary)
        except Exception as exc:
            self.metrics_service.log_request_trace(
                route=route,
                session_id=session_id,
                model_name=model_name,
                input_preview=user_input[:200],
                anonymized_preview=anonymized.anonymized_text[:200],
                pii_entities=anonymized.entity_types,
                guideline_ids=[item.document_id for item in guidelines],
                cache_hit=False,
                compression_ratio=self._compression_ratio(compression),
                llm_usage_id=None,
                response_preview=fallback_text[:200],
            )
            if self.tracing_service is not None:
                self.tracing_service.end_span(
                    trace_run_id,
                    outputs={
                        "result_type": "fallback_exception",
                        "cache_hit": False,
                        "model_name": model_name,
                        "workflow_summary": workflow_summary,
                    },
                    error=str(exc),
                )
            return PromptExecutionResult(text=fallback_text, workflow_summary=workflow_summary)

    @staticmethod
    def _compression_ratio(compression: CompressionResult) -> float:
        if compression.original_chars <= 0:
            return 1.0
        return round(compression.compressed_chars / compression.original_chars, 4)

    def _workflow_summary(
        self,
        *,
        pii_entities: list[str],
        guideline_ids: list[str],
        compression: CompressionResult,
        cache_hit: bool,
    ) -> str:
        pii_text = ", ".join(pii_entities) if pii_entities else "none"
        guidelines = ", ".join(guideline_ids) if guideline_ids else "none"
        ratio = self._compression_ratio(compression)
        return (
            f"PII anonymized: {pii_text}. "
            f"FAISS guideline retrieval: {guidelines}. "
            f"Prompt compression: {compression.strategy} {compression.original_chars}->{compression.compressed_chars} chars "
            f"({ratio:.0%} retained). "
            f"Semantic cache: {'hit' if cache_hit else 'miss'}."
        )

    @staticmethod
    def _normalize_query(query: str) -> str:
        return re.sub(r"\s+", " ", query.strip().lower())

    @staticmethod
    def _query_tokens(query: str) -> list[str]:
        if re.search(r"[a-z]", query):
            stop = {"show", "me", "with", "and", "for", "the", "under", "find"}
            return [token for token in re.findall(r"[a-z0-9]+", query) if token not in stop and len(token) > 1]
        return [token for token in query.split(" ") if token]

    @staticmethod
    def _detect_language(query: str) -> str:
        has_hira = bool(re.search(r"[\u3040-\u309F]", query))
        has_kata = bool(re.search(r"[\u30A0-\u30FF]", query))
        if has_hira and not has_kata:
            return "ja_hiragana"
        if has_kata and not has_hira:
            return "ja_katakana"
        if has_hira or has_kata:
            return "ja_mixed"
        return "en"

    @staticmethod
    def _spelling_suggestion(query: str) -> str | None:
        normalized = re.sub(r"([a-zA-Zぁ-ゟァ-ヿ])\1{2,}", r"\1\1", query.strip())
        if normalized != query.strip():
            return normalized
        return None

    def _heuristic_rerank(
        self,
        query: str,
        candidates: list[ProductRecord],
        final_limit: int,
    ) -> tuple[list[ProductRecord], str | None, str | None]:
        normalized_query = self._normalize_query(query)
        tokens = self._query_tokens(normalized_query)
        language = self._detect_language(normalized_query)
        suggested = self._spelling_suggestion(query)
        include_terms, exclude_terms = self._fallback_term_profile(normalized_query, tokens)

        scored: list[tuple[ProductRecord, int]] = []
        for product in candidates:
            hay = f"{product.product_name} {product.category_name} {product.description}".lower()
            if tokens and not any(token in hay for token in tokens):
                continue
            if include_terms and not any(term in hay for term in include_terms):
                continue
            if exclude_terms and any(term in hay for term in exclude_terms):
                continue
            overlap = sum(1 for token in tokens if token in hay)
            scored.append((product, overlap))

        if not scored:
            filtered = self._filter_by_terms(candidates, include_terms, exclude_terms)
            if filtered:
                return filtered[:final_limit], suggested, language
            return candidates[:final_limit], suggested, language

        scored.sort(key=lambda item: (item[1], item[0].rating, item[0].review_count), reverse=True)
        return [product for product, _ in scored[:final_limit]], suggested, language

    @staticmethod
    def _normalize_term_list(raw: object) -> list[str]:
        if not isinstance(raw, list):
            return []
        terms: list[str] = []
        for item in raw:
            text = str(item or "").strip().lower()
            if text and text not in terms:
                terms.append(text)
        return terms[:8]

    @staticmethod
    def _filter_by_terms(
        products: list[ProductRecord],
        include_terms: list[str],
        exclude_terms: list[str],
    ) -> list[ProductRecord]:
        if not include_terms and not exclude_terms:
            return products
        out: list[ProductRecord] = []
        for product in products:
            hay = f"{product.product_name} {product.category_name} {product.root_category_name} {product.description}".lower()
            if include_terms and not any(term in hay for term in include_terms):
                continue
            if exclude_terms and any(term in hay for term in exclude_terms):
                continue
            out.append(product)
        return out

    @staticmethod
    def _fallback_term_profile(normalized_query: str, tokens: list[str]) -> tuple[list[str], list[str]]:
        include_terms = [token for token in tokens if len(token) >= 3][:6]
        exclude_terms: list[str] = []
        if "bar" in normalized_query and "protein" in normalized_query:
            exclude_terms.extend(["powder", "protein powder"])
        return include_terms, exclude_terms

    @staticmethod
    def _parse_json(text: str) -> dict:
        cleaned = (text or "").strip()
        if not cleaned:
            return {}
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

    @staticmethod
    def _fallback_chat_reply(user_message: str, product: ProductRecord, summary: dict) -> str:
        text = user_message.lower()
        if any(k in text for k in ["price", "cost", "how much", "値段", "価格", "いくら"]):
            return f"The price is {product.currency} {product.final_price:.2f}."
        if any(k in text for k in ["delivery", "pickup", "available", "在庫", "配送", "受取"]):
            return (
                f"Availability: delivery is {'available' if product.available_for_delivery else 'not available'}, "
                f"pickup is {'available' if product.available_for_pickup else 'not available'}."
            )
        if any(k in text for k in ["ingredient", "成分"]):
            if product.ingredients:
                return f"Ingredients: {product.ingredients[:500]}"
            return "Ingredients are not listed for this product."

        sentiment = summary.get("sentiment", "mixed")
        return (
            f"{product.product_name} is rated {product.rating:.1f} from {product.review_count} reviews, "
            f"with overall {sentiment} feedback."
        )
