import sqlite3
from collections.abc import Iterable

from app.models.product import ProductRecord
from app.utils.config import DATA_DB_PATH
from app.utils.parsers import normalize_text, parse_bool, parse_float, parse_int, safe_json_loads


class ProductRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(DATA_DB_PATH if db_path is None else db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _to_record(self, row: sqlite3.Row) -> ProductRecord:
        return ProductRecord(
            product_id=str(row["product_id"] or ""),
            product_name=normalize_text(row["product_name"]),
            category_name=normalize_text(row["category_name"]),
            root_category_name=normalize_text(row["root_category_name"]),
            description=normalize_text(row["description"]),
            final_price=parse_float(row["final_price"]),
            currency=normalize_text(row["currency"]) or "USD",
            rating=parse_float(row["rating"]),
            review_count=parse_int(row["review_count"]),
            brand=normalize_text(row["brand"]),
            main_image=normalize_text(row["main_image"]).strip('"'),
            available_for_delivery=parse_bool(row["available_for_delivery"]),
            available_for_pickup=parse_bool(row["available_for_pickup"]),
            specifications=safe_json_loads(row["specifications"], []),
            colors=safe_json_loads(row["colors"], []),
            ingredients=normalize_text(row["ingredients"]),
            customer_reviews=safe_json_loads(row["customer_reviews"], []),
            seller=normalize_text(row["seller"]),
            other_attributes=safe_json_loads(row["other_attributes"], []),
        )

    def all_products(self) -> list[ProductRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM products").fetchall()
        return [self._to_record(row) for row in rows if row["product_id"]]

    def get_by_product_id(self, product_id: str) -> ProductRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE product_id = ? LIMIT 1",
                (product_id,),
            ).fetchone()
        return self._to_record(row) if row else None

    def get_by_product_ids(self, product_ids: Iterable[str]) -> list[ProductRecord]:
        ids = [pid for pid in product_ids if pid]
        if not ids:
            return []
        placeholders = ",".join(["?"] * len(ids))
        query = f"SELECT * FROM products WHERE product_id IN ({placeholders})"
        with self._connect() as conn:
            rows = conn.execute(query, ids).fetchall()
        return [self._to_record(row) for row in rows]
