import re
from dataclasses import dataclass


@dataclass
class ParsedSearchIntent:
    query: str
    max_price: float | None
    min_rating: float | None
    inferred_category: str | None


def parse_search_intent(query: str) -> ParsedSearchIntent:
    text = query.lower()

    price_match = re.search(r"(?:under|below|less than)\s*\$?\s*(\d+(?:\.\d+)?)", text)
    max_price = float(price_match.group(1)) if price_match else None

    rating_match = re.search(r"(?:rating|rated|reviews?)\s*(?:above|over|at least|>=)?\s*(\d(?:\.\d)?)", text)
    min_rating = float(rating_match.group(1)) if rating_match else None
    if "good review" in text or "highly rated" in text:
        min_rating = max(min_rating or 0.0, 4.0)

    category_hint = None
    for candidate in [
        "skincare",
        "shampoo",
        "beauty",
        "protein",
        "curtains",
        "home",
        "makeup",
        "supplement",
    ]:
        if candidate in text:
            category_hint = candidate
            break

    return ParsedSearchIntent(
        query=query,
        max_price=max_price,
        min_rating=min_rating,
        inferred_category=category_hint,
    )
