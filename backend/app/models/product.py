from dataclasses import dataclass
from typing import Any


@dataclass
class ProductRecord:
    product_id: str
    product_name: str
    category_name: str
    root_category_name: str
    description: str
    final_price: float
    currency: str
    rating: float
    review_count: int
    brand: str
    main_image: str
    available_for_delivery: bool
    available_for_pickup: bool
    specifications: list[dict[str, Any]]
    colors: list[str]
    ingredients: str
    customer_reviews: list[dict[str, Any]]
    seller: str
    other_attributes: list[dict[str, Any]]

    def breadcrumb(self) -> str:
        return f"Home > {self.root_category_name or 'Unknown'} > {self.category_name or 'Unknown'} > {self.product_name}"
