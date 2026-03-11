GUIDELINE_DOCUMENTS = [
    {
        "id": "chat_core",
        "route": "chat",
        "title": "Chat Product Assistant Rules",
        "text": (
            "You are a product assistant for e-commerce conversations. Use only product facts provided by the system. "
            "Answer directly, stay concise, avoid fabrication, and prioritize price, availability, rating, ingredients, "
            "and review-backed quality signals when relevant."
        ),
    },
    {
        "id": "search_core",
        "route": "search",
        "title": "Search Retrieval Rules",
        "text": (
            "Prepare and rerank product search results with high precision. Preserve user intent, tolerate small typos, "
            "avoid sibling-category mistakes, and prefer fewer results over irrelevant results when confidence is low."
        ),
    },
    {
        "id": "gdpr_pii",
        "route": "all",
        "title": "GDPR PII Handling",
        "text": (
            "Before external model calls, detect and anonymize direct identifiers such as emails, phone numbers, card numbers, "
            "IP addresses, SSNs, IBANs, and postal addresses. Minimize personal data exposure and retain only the semantics "
            "required to answer the request."
        ),
    },
    {
        "id": "prompt_budget",
        "route": "all",
        "title": "Prompt Budget Management",
        "text": (
            "Compress repeated instructions and retrieved context before model invocation. Preserve policy constraints, "
            "product facts, user intent, and disambiguating details while removing redundancy to reduce token cost."
        ),
    },
    {
        "id": "cache_rules",
        "route": "all",
        "title": "Semantic Cache Rules",
        "text": (
            "Reuse prior answers only when the anonymized prompt is semantically similar and the request route and model "
            "match. Prefer a fresh model call when similarity is weak or context-specific facts may have changed."
        ),
    },
]
