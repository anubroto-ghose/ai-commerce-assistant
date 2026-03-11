from typing import Any

from chromadb import PersistentClient
from chromadb.utils import embedding_functions

from app.models.product import ProductRecord
from app.tools.semantic import SimpleSemanticIndex
from app.utils.config import CHROMA_DIR, OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL


class RetrievalService:
    def __init__(self) -> None:
        self.index = SimpleSemanticIndex()
        self.chroma_client = None
        self.use_chroma = bool(OPENAI_API_KEY)
        self.collection: Any | None = None
        if self.use_chroma:
            try:
                self.chroma_client = PersistentClient(path=str(CHROMA_DIR))
                embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=OPENAI_API_KEY,
                    model_name=OPENAI_EMBEDDING_MODEL,
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name="walmart_products",
                    embedding_function=embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                self.chroma_client = None
                self.collection = None
                self.use_chroma = False
        self._loaded = False

    @staticmethod
    def _doc_text(product: ProductRecord) -> str:
        review_text = " ".join(str(r.get("review", "")) for r in product.customer_reviews[:5])
        specs = " ".join(f"{s.get('name', '')} {s.get('value', '')}" for s in product.specifications)
        colors = " ".join(product.colors)
        return " ".join(
            [
                product.product_name,
                product.description,
                product.category_name,
                product.root_category_name,
                product.ingredients,
                product.brand,
                specs,
                colors,
                review_text,
            ]
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # rough estimate used only for batching; OpenAI tokenization is model-specific
        return max(1, len(text) // 4)

    def _batched_records(self, products: list[ProductRecord]) -> list[tuple[list[str], list[str], list[dict[str, Any]]]]:
        max_est_tokens = 120_000
        max_items = 64
        batches: list[tuple[list[str], list[str], list[dict[str, Any]]]] = []

        ids_batch: list[str] = []
        docs_batch: list[str] = []
        meta_batch: list[dict[str, Any]] = []
        token_total = 0

        for product in products:
            doc = self._doc_text(product)
            est = self._estimate_tokens(doc)
            metadata = {
                "product_id": product.product_id,
                "product_name": product.product_name,
                "category_name": product.category_name,
                "root_category_name": product.root_category_name,
                "rating": product.rating,
                "final_price": product.final_price,
            }

            if ids_batch and (token_total + est > max_est_tokens or len(ids_batch) >= max_items):
                batches.append((ids_batch, docs_batch, meta_batch))
                ids_batch, docs_batch, meta_batch = [], [], []
                token_total = 0

            ids_batch.append(product.product_id)
            docs_batch.append(doc)
            meta_batch.append(metadata)
            token_total += est

        if ids_batch:
            batches.append((ids_batch, docs_batch, meta_batch))
        return batches

    def build_index(self, products: list[ProductRecord]) -> None:
        for product in products:
            self.index.add(product.product_id, self._doc_text(product))

        if self.use_chroma and self.collection is not None:
            for ids, documents, metadatas in self._batched_records(products):
                self.collection.upsert(documents=documents, ids=ids, metadatas=metadatas)
        self._loaded = True

    def semantic_rank(self, query: str, products: list[ProductRecord]) -> list[tuple[ProductRecord, float]]:
        product_map = {product.product_id: product for product in products}
        if self.use_chroma and self.collection is not None:
            result = self.collection.query(
                query_texts=[query],
                n_results=min(100, max(10, len(products))),
                include=["distances"],
            )
            ids = (result.get("ids") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            ranked: list[tuple[ProductRecord, float]] = []
            for product_id, distance in zip(ids, distances):
                product = product_map.get(product_id)
                if product is None:
                    continue
                similarity = 1.0 - float(distance)
                ranked.append((product, similarity))
            return ranked

        ranked = [(product, self.index.score(query, product.product_id)) for product in products]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    @property
    def loaded(self) -> bool:
        return self._loaded
