import httpx
import json
import asyncio
from typing import List
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
from rich.console import Console
from rich.table import Table
from rich import box

# Load environment variables from the .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in environment variables")

client = OpenAI()
console = Console()

# ─── Data Models ──────────────────────────────────────────────────────────────

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
    products: List[ProductResult]

# ─── Golden Dataset ────────────────────────────────────────────────────────────

def create_golden_dataset():
    return [
        {"query": "laptop",         "limit": 5,  "expected_category": "Electronics",  "expected_keywords": ["laptop", "computer", "notebook"]},
        {"query": "wireless mouse", "limit": 3,  "expected_category": "Electronics",  "expected_keywords": ["mouse", "wireless", "bluetooth"]},
        {"query": "gaming chair",   "limit": 10, "expected_category": "Furniture",    "expected_keywords": ["gaming", "chair", "ergonomic"]},
        
        # {"query": "smartphone",     "limit": 5,  "expected_category": "Electronics",  "expected_keywords": ["smartphone", "mobile", "cell phone"]},
        # {"query": "headphones",     "limit": 4,  "expected_category": "Electronics",  "expected_keywords": ["headphones", "audio", "music"]},
        # {"query": "office desk",    "limit": 7,  "expected_category": "Furniture",    "expected_keywords": ["desk", "office", "workstation"]},
        # {"query": "coffee maker",   "limit": 5,  "expected_category": "Appliances",  "expected_keywords": ["coffee", "maker", "brewer"]},
        # {"query": "refrigerator",   "limit": 3,  "expected_category": "Appliances",  "expected_keywords": ["fridge", "refrigerator", "cooler"]},
        # {"query": "running shoes",  "limit": 6,  "expected_category": "Footwear",    "expected_keywords": ["shoes", "running", "sneakers"]},
        # {"query": "vacuum cleaner", "limit": 4,  "expected_category": "Appliances",  "expected_keywords": ["vacuum", "cleaner", "floor"]},
        
        {"query": "sofa",           "limit": 10, "expected_category": "Furniture",    "expected_keywords": ["sofa", "couch", "furniture"]},
        {"query": "tablet",         "limit": 5,  "expected_category": "Electronics",  "expected_keywords": ["tablet", "ipad", "slate"]},
        {"query": "kitchen blender", "limit": 3, "expected_category": "Appliances",  "expected_keywords": ["blender", "kitchen", "mixer"]},
        {"query": "winter jacket",  "limit": 6,  "expected_category": "Apparel",      "expected_keywords": ["jacket", "winter", "coat"]},
        {"query": "bicycle",        "limit": 5,  "expected_category": "Sports",       "expected_keywords": ["bike", "bicycle", "cycling"]},
        {"query": "golf clubs",     "limit": 7,  "expected_category": "Sports",       "expected_keywords": ["golf", "clubs", "sports"]},
        # {"query": "yoga mat",       "limit": 4,  "expected_category": "Sports",       "expected_keywords": ["yoga", "mat", "exercise"]},
        
        # {"query": "sneakers",       "limit": 5,  "expected_category": "Footwear",    "expected_keywords": ["sneakers", "shoes", "sports shoes"]},
        # {"query": "formal shirt",   "limit": 6,  "expected_category": "Apparel",      "expected_keywords": ["shirt", "formal", "business attire"]},
        # {"query": "slippers",       "limit": 3,  "expected_category": "Footwear",    "expected_keywords": ["slippers", "house shoes", "footwear"]},
        # {"query": "kitchen knife",  "limit": 4,  "expected_category": "Appliances",  "expected_keywords": ["knife", "kitchen", "cutlery"]},
        
        # {"query": "fitness tracker", "limit": 4, "expected_category": "Electronics", "expected_keywords": ["fitness", "tracker", "health"]},
        # {"query": "smartwatch",     "limit": 4,  "expected_category": "Electronics", "expected_keywords": ["smartwatch", "watch", "wearable"]},
        # {"query": "digital camera", "limit": 5,  "expected_category": "Electronics", "expected_keywords": ["camera", "digital", "photography"]},
        # {"query": "dining table",   "limit": 6,  "expected_category": "Furniture",   "expected_keywords": ["table", "dining", "furniture"]},
        # {"query": "gaming laptop",  "limit": 5,  "expected_category": "Electronics", "expected_keywords": ["gaming", "laptop", "computer"]},
        
        # {"query": "microwave",      "limit": 4,  "expected_category": "Appliances", "expected_keywords": ["microwave", "oven", "cooking"]},
        # {"query": "iron",           "limit": 4,  "expected_category": "Appliances", "expected_keywords": ["iron", "clothing", "press"]},
        
        # {"query": "スマートフォン",           "limit": 5,  "expected_category": "Electronics",  "expected_keywords": ["smartphone", "mobile", "cell phone"]},
        # {"query": "ノートパソコン",         "limit": 5,  "expected_category": "Electronics",  "expected_keywords": ["laptop", "computer", "notebook"]},
        # {"query": "ゲーミングチェア",   "limit": 10, "expected_category": "Furniture",    "expected_keywords": ["gaming", "chair", "ergonomic"]},
        # {"query": "オフィスデスク",    "limit": 7,  "expected_category": "Furniture",    "expected_keywords": ["desk", "office", "workstation"]},
        # {"query": "コーヒーメーカー",   "limit": 5,  "expected_category": "Appliances",  "expected_keywords": ["coffee", "maker", "brewer"]},
        
        # {"query": "ランニングシューズ",  "limit": 6,  "expected_category": "Footwear",    "expected_keywords": ["shoes", "running", "sneakers"]},
        # {"query": "タブレット",         "limit": 5,  "expected_category": "Electronics",  "expected_keywords": ["tablet", "ipad", "slate"]},
        # {"query": "ウィンタージャケット",  "limit": 6,  "expected_category": "Apparel",      "expected_keywords": ["jacket", "winter", "coat"]},
        # {"query": "ゴルフクラブ",     "limit": 7,  "expected_category": "Sports",       "expected_keywords": ["golf", "clubs", "sports"]},
        # {"query": "ヨガマット",       "limit": 4,  "expected_category": "Sports",       "expected_keywords": ["yoga", "mat", "exercise"]},
        
        {"query": "スニーカー",       "limit": 5,  "expected_category": "Footwear",    "expected_keywords": ["sneakers", "shoes", "sports shoes"]},
        {"query": "フォーマルシャツ",   "limit": 6,  "expected_category": "Apparel",      "expected_keywords": ["shirt", "formal", "business attire"]},
        {"query": "スリッパ",       "limit": 3,  "expected_category": "Footwear",    "expected_keywords": ["slippers", "house shoes", "footwear"]},
        {"query": "キッチンナイフ",  "limit": 4,  "expected_category": "Appliances",  "expected_keywords": ["knife", "kitchen", "cutlery"]},
        
        {"query": "フィットネストラッカー", "limit": 4, "expected_category": "Electronics", "expected_keywords": ["fitness", "tracker", "health"]},
        {"query": "スマートウォッチ",     "limit": 4,  "expected_category": "Electronics", "expected_keywords": ["smartwatch", "watch", "wearable"]},
        {"query": "デジタルカメラ", "limit": 5,  "expected_category": "Electronics", "expected_keywords": ["camera", "digital", "photography"]},
        ]
# ─── API Call ─────────────────────────────────────────────────────────────────

API_URL = "http://127.0.0.1:8000/api/search"

async def send_search_request(payload: dict):
    async with httpx.AsyncClient(timeout=200.0) as http_client:
        try:
            response = await http_client.post(API_URL, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                console.print(f"[red]HTTP Error {response.status_code}[/red]")
                return None
        except Exception as e:
            console.print(f"[red]Request failed: {e}[/red]")
            return None

# ─── LLM Judge ────────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are an expert e-commerce search quality evaluator.
You will be given a search query and a list of product results, including each product's name,
description snippet, brand, price, and catalog category metadata.

CRITICAL EVALUATION RULES — read carefully before scoring:

1. PRODUCT RELEVANCE is determined by the product's ACTUAL IDENTITY (name + description),
   NOT by its catalog category. A laptop filed under "Seasonal > High School Supplies" is
   still a laptop — do NOT flag it as a false positive due to miscategorisation.

2. FALSE POSITIVES = products whose name AND description are genuinely unrelated to the query.
   Example: a bra returned for "wireless mouse" is a false positive.
   Example: an HP Victus laptop returned for "laptop" is NOT a false positive — it IS a laptop.

3. CATALOG METADATA ISSUES = separately track products where the catalog category is wrong
   or misleading even though the product itself is relevant. This is a data quality bug,
   not a relevance bug.

4. CATEGORY ACCURACY SCORE should reflect whether catalog categories align with query intent.
   Penalise if correct products are misfiled — but do not confuse this with false positives.

You MUST respond with ONLY a valid JSON object — no explanation, no markdown, no backticks.

{
  "relevance_score": <int 1-10>,
  "precision_score": <int 1-10>,
  "diversity_score": <int 1-10>,
  "category_accuracy_score": <int 1-10>,
  "bias_score": <int 1-10>,
  "price_range_score": <int 1-10>,
  "overall_score": <float 1-10>,
  "relevance_comment": "<string>",
  "precision_comment": "<string>",
  "diversity_comment": "<string>",
  "category_comment": "<string>",
  "bias_comment": "<string>",
  "false_positives": ["<product_name>"],
  "catalog_metadata_issues": [
    {"product": "<name>", "filed_under": "<actual category>", "should_be": "<correct category>"}
  ],
  "top_issues": ["<string>"],
  "summary": "<one sentence overall verdict>"
}"""

async def judge_search_response(query: str, products: list, expected_keywords: list) -> dict:
    prompt = {
        "query": query,
        "expected_keywords": expected_keywords,
        "returned_products": [
            {
                "name": p.get("product_name", ""),
                "category": p.get("category_name", ""),
                "root_category": p.get("root_category_name", ""),
                "price": p.get("price", 0),
                "brand": p.get("brand", ""),
                "description_snippet": p.get("description", "")[:200],
            }
            for p in products
        ]
    }

    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": json.dumps(prompt)}
            ],
            temperature=0,
            response_format={"type": "json_object"}   # Forces JSON output — fixes the N/A bug
        )
        raw = result.choices[0].message.content.strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        console.print(f"[red]JSON parse error: {e}\nRaw: {raw[:300]}[/red]")
        return {}
    except Exception as e:
        console.print(f"[red]LLM judge error: {e}[/red]")
        return {}

# ─── Heuristic Checks (rule-based, no LLM cost) ───────────────────────────────

def run_heuristic_checks(query: str, response: dict, expected_keywords: list) -> dict:
    products = response.get("products", [])
    total = len(products)
    if total == 0:
        return {"zero_results": True}

    checks = {}

    # Keyword match rate
    matched = sum(
        1 for p in products
        if any(kw.lower() in p.get("product_name", "").lower() or
               kw.lower() in p.get("description", "").lower()
               for kw in expected_keywords)
    )
    checks["keyword_match_rate"] = round(matched / total * 100, 1)

    # Brand concentration (bias signal)
    brands = [p.get("brand", "Unknown") for p in products]
    brand_counts = {b: brands.count(b) for b in set(brands)}
    top_brand, top_count = max(brand_counts.items(), key=lambda x: x[1])
    checks["brand_concentration"] = f"{top_brand} ({top_count}/{total})"
    checks["brand_concentration_pct"] = round(top_count / total * 100, 1)

    # Price spread
    prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
    if prices:
        checks["price_min"] = min(prices)
        checks["price_max"] = max(prices)
        checks["price_spread"] = round(max(prices) - min(prices), 2)
    else:
        checks["price_min"] = checks["price_max"] = checks["price_spread"] = 0

    # Avg rating
    ratings = [p.get("rating", 0) for p in products if p.get("rating", 0) > 0]
    checks["avg_rating"] = round(sum(ratings) / len(ratings), 2) if ratings else 0

    # Out-of-category products
    query_lower = query.lower()
    off_topic = [
        p.get("product_name", "")
        for p in products
        if query_lower not in p.get("product_name", "").lower()
        and not any(kw in p.get("product_name", "").lower() for kw in expected_keywords)
    ]
    checks["off_topic_products"] = off_topic
    checks["off_topic_count"] = len(off_topic)

    return checks

# ─── Summary Table ─────────────────────────────────────────────────────────────

def print_summary_table(results: list):
    table = Table(
        title="🔍 Search Quality Evaluation — Full Report",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold white on dark_blue"
    )
    table.add_column("Query",              style="cyan bold",   width=14)
    table.add_column("Overall",            style="yellow bold", width=8,  justify="center")
    table.add_column("Relevance",          style="green",       width=10, justify="center")
    table.add_column("Precision",          style="green",       width=10, justify="center")
    table.add_column("Diversity",          style="green",       width=10, justify="center")
    table.add_column("Category Acc.",      style="green",       width=12, justify="center")
    table.add_column("Bias (10=clean)",    style="magenta",     width=14, justify="center")
    table.add_column("False +ves",         style="red",         width=10, justify="center")
    table.add_column("KW Match %",         style="blue",        width=11, justify="center")
    table.add_column("Brand Concentration",style="magenta",     width=20, justify="center")
    table.add_column("Price Range",        style="blue",        width=16, justify="center")
    table.add_column("Top Issues",         style="yellow",      width=40)

    for r in results:
        j = r["judge"]
        h = r["heuristics"]
        overall = j.get("overall_score", "N/A")
        color = "green" if isinstance(overall, (int,float)) and overall >= 7 else \
                "yellow" if isinstance(overall, (int,float)) and overall >= 4 else "red"

        issues = "\n".join(f"• {i}" for i in j.get("top_issues", []))
        fp_names = j.get("false_positives", [])
        if fp_names:
            short_names = [n.split(",")[0][:25] for n in fp_names[:2]]
            fp_display = f"{len(fp_names)}: {', '.join(short_names)}"
        else:
            fp_display = "0"

        table.add_row(
            r["query"],
            f"[{color}]{overall}[/{color}]",
            str(j.get("relevance_score", "N/A")),
            str(j.get("precision_score", "N/A")),
            str(j.get("diversity_score", "N/A")),
            str(j.get("category_accuracy_score", "N/A")),
            str(j.get("bias_score", "N/A")),
            fp_display,
            f"{h.get('keyword_match_rate','N/A')}%",
            h.get("brand_concentration", "N/A"),
            f"${h.get('price_min',0):.0f}–${h.get('price_max',0):.0f}",
            issues or "None identified",
        )

    console.print(table)

def print_detail_panels(results: list):
    """Print per-query narrative summaries."""
    for r in results:
        j = r["judge"]
        console.rule(f"[bold cyan] Detailed Report: '{r['query']}' [/bold cyan]")
        console.print(f"[bold]Summary:[/bold]    {j.get('summary', 'N/A')}")
        console.print(f"[bold]Relevance:[/bold]  {j.get('relevance_comment', '')}")
        console.print(f"[bold]Precision:[/bold]  {j.get('precision_comment', '')}")
        console.print(f"[bold]Diversity:[/bold]  {j.get('diversity_comment', '')}")
        console.print(f"[bold]Category:[/bold]   {j.get('category_comment', '')}")
        console.print(f"[bold]Bias:[/bold]       {j.get('bias_comment', '')}")

        # Catalog metadata issues — product IS relevant but misfiled in the catalog
        catalog_issues = j.get("catalog_metadata_issues", [])
        if catalog_issues:
            console.print("[bold yellow]Catalog metadata issues (relevant product, wrong category):[/bold yellow]")
            for ci in catalog_issues:
                prod = str(ci.get("product", "?"))[:50]
                filed = ci.get("filed_under", "?")
                should = ci.get("should_be", "?")
                console.print(f"  [cyan]{prod}[/cyan]  filed: [red]{filed}[/red]  should be: [green]{should}[/green]")

        # Heuristic off-topic check
        off = r["heuristics"].get("off_topic_products", [])
        if off:
            truncated = [(name[:60] + "...") if len(name) > 60 else name for name in off]
            console.print(f"[bold red]Off-topic (heuristic):[/bold red] {', '.join(truncated)}")
        console.print()

# ─── Main Test Runner ──────────────────────────────────────────────────────────

async def test_golden_dataset():
    golden_dataset = create_golden_dataset()
    all_results = []

    for data in golden_dataset:
        console.print(f"\n[bold cyan]▶ Testing query:[/bold cyan] {data['query']}")

        response = await send_search_request({"query": data["query"], "limit": data["limit"]})
        if not response:
            console.print("[red]  No response — skipping.[/red]")
            continue

        products = response.get("products", [])
        console.print(f"  Returned {len(products)} products.")

        # LLM judge
        judge_result = await judge_search_response(
            query=data["query"],
            products=products,
            expected_keywords=data["expected_keywords"]
        )

        # Heuristic checks
        heuristic_result = run_heuristic_checks(
            query=data["query"],
            response=response,
            expected_keywords=data["expected_keywords"]
        )

        all_results.append({
            "query": data["query"],
            "judge": judge_result,
            "heuristics": heuristic_result,
        })

    console.print("\n")
    print_summary_table(all_results)
    print_detail_panels(all_results)

def main():
    asyncio.run(test_golden_dataset())

if __name__ == "__main__":
    main()