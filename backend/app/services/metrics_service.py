import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.model_pricing import MODEL_PRICING_TABLE, TOKENS_PER_MILLION, resolve_model_pricing
from app.utils.config import METRICS_DB_PATH


class MetricsService:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(METRICS_DB_PATH if db_path is None else db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS model_costs (
                    model_key TEXT NOT NULL,
                    context_threshold INTEGER,
                    note TEXT NOT NULL DEFAULT '',
                    input_cost_per_million REAL NOT NULL,
                    cached_input_cost_per_million REAL,
                    output_cost_per_million REAL,
                    PRIMARY KEY (model_key, note)
                );

                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    route TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_cost_usd REAL NOT NULL DEFAULT 0,
                    cache_hit INTEGER NOT NULL DEFAULT 0,
                    pii_entities_count INTEGER NOT NULL DEFAULT 0,
                    compressed_chars_before INTEGER NOT NULL DEFAULT 0,
                    compressed_chars_after INTEGER NOT NULL DEFAULT 0,
                    workflow_summary TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS request_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    route TEXT NOT NULL,
                    session_id TEXT,
                    model_name TEXT,
                    input_preview TEXT NOT NULL DEFAULT '',
                    anonymized_preview TEXT NOT NULL DEFAULT '',
                    pii_entities_json TEXT NOT NULL DEFAULT '[]',
                    guideline_ids_json TEXT NOT NULL DEFAULT '[]',
                    cache_hit INTEGER NOT NULL DEFAULT 0,
                    compression_ratio REAL NOT NULL DEFAULT 1,
                    llm_usage_id INTEGER,
                    response_preview TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (llm_usage_id) REFERENCES llm_usage(id)
                );
                """
            )
            conn.executemany(
                """
                INSERT OR REPLACE INTO model_costs (
                    model_key,
                    context_threshold,
                    note,
                    input_cost_per_million,
                    cached_input_cost_per_million,
                    output_cost_per_million
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        entry.model_key,
                        entry.context_threshold,
                        entry.note,
                        entry.input_cost_per_million,
                        entry.cached_input_cost_per_million,
                        entry.output_cost_per_million,
                    )
                    for entry in MODEL_PRICING_TABLE
                ],
            )
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int,
    ) -> float:
        pricing = resolve_model_pricing(model_name, input_tokens=input_tokens)
        if pricing is None:
            return 0.0

        uncached_input = max(0, input_tokens - cached_input_tokens)
        input_cost = (uncached_input / TOKENS_PER_MILLION) * pricing.input_cost_per_million
        cached_cost = 0.0
        if pricing.cached_input_cost_per_million is not None:
            cached_cost = (cached_input_tokens / TOKENS_PER_MILLION) * pricing.cached_input_cost_per_million
        output_cost = 0.0
        if pricing.output_cost_per_million is not None:
            output_cost = (output_tokens / TOKENS_PER_MILLION) * pricing.output_cost_per_million
        return round(input_cost + cached_cost + output_cost, 8)

    def log_llm_usage(
        self,
        *,
        route: str,
        model_name: str,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int,
        cache_hit: bool,
        pii_entities_count: int,
        compressed_chars_before: int,
        compressed_chars_after: int,
        workflow_summary: str,
    ) -> int:
        total_cost_usd = self.calculate_cost(
            model_name=model_name,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
        )
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO llm_usage (
                    created_at,
                    route,
                    model_name,
                    input_tokens,
                    cached_input_tokens,
                    output_tokens,
                    total_cost_usd,
                    cache_hit,
                    pii_entities_count,
                    compressed_chars_before,
                    compressed_chars_after,
                    workflow_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    route,
                    model_name,
                    input_tokens,
                    cached_input_tokens,
                    output_tokens,
                    total_cost_usd,
                    int(cache_hit),
                    pii_entities_count,
                    compressed_chars_before,
                    compressed_chars_after,
                    workflow_summary,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def log_request_trace(
        self,
        *,
        route: str,
        session_id: str | None,
        model_name: str | None,
        input_preview: str,
        anonymized_preview: str,
        pii_entities: list[str],
        guideline_ids: list[str],
        cache_hit: bool,
        compression_ratio: float,
        llm_usage_id: int | None,
        response_preview: str,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO request_traces (
                    created_at,
                    route,
                    session_id,
                    model_name,
                    input_preview,
                    anonymized_preview,
                    pii_entities_json,
                    guideline_ids_json,
                    cache_hit,
                    compression_ratio,
                    llm_usage_id,
                    response_preview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    route,
                    session_id,
                    model_name,
                    input_preview,
                    anonymized_preview,
                    json.dumps(pii_entities),
                    json.dumps(guideline_ids),
                    int(cache_hit),
                    compression_ratio,
                    llm_usage_id,
                    response_preview,
                ),
            )
            conn.commit()

    def get_system_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS llm_calls,
                    COALESCE(SUM(total_cost_usd), 0) AS total_cost_usd,
                    COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                    COALESCE(SUM(cached_input_tokens), 0) AS total_cached_input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                    COALESCE(SUM(cache_hit), 0) AS total_cache_hits,
                    COALESCE(SUM(pii_entities_count), 0) AS total_pii_entities
                FROM llm_usage
                """
            ).fetchone()
            by_route = conn.execute(
                """
                SELECT
                    route,
                    COUNT(*) AS calls,
                    ROUND(COALESCE(SUM(total_cost_usd), 0), 6) AS total_cost_usd,
                    COALESCE(SUM(cache_hit), 0) AS cache_hits
                FROM llm_usage
                GROUP BY route
                ORDER BY calls DESC, route ASC
                """
            ).fetchall()
            recent_traces = conn.execute(
                """
                SELECT *
                FROM request_traces
                ORDER BY id DESC
                LIMIT 10
                """
            ).fetchall()
        return {
            "database_path": self.db_path,
            "llm_calls": int(totals["llm_calls"] or 0),
            "total_cost_usd": round(float(totals["total_cost_usd"] or 0), 6),
            "total_input_tokens": int(totals["total_input_tokens"] or 0),
            "total_cached_input_tokens": int(totals["total_cached_input_tokens"] or 0),
            "total_output_tokens": int(totals["total_output_tokens"] or 0),
            "total_cache_hits": int(totals["total_cache_hits"] or 0),
            "total_pii_entities": int(totals["total_pii_entities"] or 0),
            "by_route": [
                {
                    "route": row["route"],
                    "calls": int(row["calls"] or 0),
                    "total_cost_usd": float(row["total_cost_usd"] or 0),
                    "cache_hits": int(row["cache_hits"] or 0),
                }
                for row in by_route
            ],
            "recent_traces": [
                {
                    "created_at": row["created_at"],
                    "route": row["route"],
                    "session_id": row["session_id"],
                    "model_name": row["model_name"],
                    "cache_hit": bool(row["cache_hit"]),
                    "compression_ratio": float(row["compression_ratio"] or 1),
                    "pii_entities": json.loads(row["pii_entities_json"] or "[]"),
                    "guideline_ids": json.loads(row["guideline_ids_json"] or "[]"),
                    "input_preview": row["input_preview"],
                    "anonymized_preview": row["anonymized_preview"],
                    "response_preview": row["response_preview"],
                }
                for row in recent_traces
            ],
        }
