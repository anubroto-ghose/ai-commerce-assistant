from app.models.product import ProductRecord
from app.schemas.api import ProductResult


def to_product_result(product: ProductRecord) -> ProductResult:
    short_description = (product.description or "")[:240]
    return ProductResult(
        product_id=product.product_id,
        product_name=product.product_name,
        description=short_description,
        price=product.final_price,
        currency=product.currency,
        rating=product.rating,
        review_count=product.review_count,
        brand=product.brand,
        main_image=product.main_image,
        category_name=product.category_name,
        root_category_name=product.root_category_name,
        breadcrumb=product.breadcrumb(),
        available_for_delivery=product.available_for_delivery,
        available_for_pickup=product.available_for_pickup,
        colors=product.colors,
        ingredients=product.ingredients,
        specifications=product.specifications,
    )
