from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=15)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    product_id: str | None = None
    session_id: str | None = None


class ProductResult(BaseModel):
    product_id: str
    product_name: str
    description: str
    price: float
    currency: str
    rating: float
    review_count: int
    brand: str
    main_image: str
    category_name: str
    root_category_name: str
    breadcrumb: str
    available_for_delivery: bool
    available_for_pickup: bool
    colors: list[str]
    ingredients: str
    specifications: list[dict]


class SearchResponse(BaseModel):
    query: str
    suggested_search: str | None = None
    detected_language: str | None = None
    interpreted_filters: dict
    total_results: int
    products: list[ProductResult]
    workflow_summary: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    needs_product_id: bool
    product_id: str | None = None
    response: str
    product_summary: dict | None = None
    alternatives: list[ProductResult] = []
    workflow_summary: str | None = None


class SystemStatsResponse(BaseModel):
    database_path: str
    llm_calls: int
    total_cost_usd: float
    total_input_tokens: int
    total_cached_input_tokens: int
    total_output_tokens: int
    total_cache_hits: int
    total_pii_entities: int
    by_route: list[dict]
    recent_traces: list[dict]
