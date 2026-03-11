import sqlite3
from pathlib import Path


MODEL_COSTS = [
    ("gpt-5.4", 272000, "<272K context length", 2.50, 0.25, 15.00),
    ("gpt-5.4", 272000, ">272K context length", 5.00, 0.50, 22.50),
    ("gpt-5.4-pro", 272000, "<272K context length", 30.00, None, 180.00),
    ("gpt-5.4-pro", 272000, ">272K context length", 60.00, None, 270.00),
    ("gpt-5.2", None, "", 1.75, 0.175, 14.00),
    ("gpt-5.1", None, "", 1.25, 0.125, 10.00),
    ("gpt-5", None, "", 1.25, 0.125, 10.00),
    ("gpt-5-mini", None, "", 0.25, 0.025, 2.00),
    ("gpt-5-nano", None, "", 0.05, 0.005, 0.40),
    ("gpt-5.3-chat-latest", None, "", 1.75, 0.175, 14.00),
    ("gpt-5.2-chat-latest", None, "", 1.75, 0.175, 14.00),
    ("gpt-5.1-chat-latest", None, "", 1.25, 0.125, 10.00),
    ("gpt-5-chat-latest", None, "", 1.25, 0.125, 10.00),
    ("gpt-5.3-codex", None, "", 1.75, 0.175, 14.00),
    ("gpt-5.2-codex", None, "", 1.75, 0.175, 14.00),
    ("gpt-5.1-codex-max", None, "", 1.25, 0.125, 10.00),
    ("gpt-5.1-codex", None, "", 1.25, 0.125, 10.00),
    ("gpt-5-codex", None, "", 1.25, 0.125, 10.00),
    ("gpt-5.2-pro", None, "", 21.00, None, 168.00),
    ("gpt-5-pro", None, "", 15.00, None, 120.00),
    ("gpt-4.1", None, "", 2.00, 0.50, 8.00),
    ("gpt-4.1-mini", None, "", 0.40, 0.10, 1.60),
    ("gpt-4.1-nano", None, "", 0.10, 0.025, 0.40),
    ("gpt-4o", None, "", 2.50, 1.25, 10.00),
    ("gpt-4o-2024-05-13", None, "", 5.00, None, 15.00),
    ("gpt-4o-mini", None, "", 0.15, 0.075, 0.60),
    ("gpt-realtime", None, "", 4.00, 0.40, 16.00),
    ("gpt-realtime-1.5", None, "", 4.00, 0.40, 16.00),
    ("gpt-realtime-mini", None, "", 0.60, 0.06, 2.40),
    ("gpt-4o-realtime-preview", None, "", 5.00, 2.50, 20.00),
    ("gpt-4o-mini-realtime-preview", None, "", 0.60, 0.30, 2.40),
    ("gpt-audio", None, "", 2.50, None, 10.00),
    ("gpt-audio-1.5", None, "", 2.50, None, 10.00),
    ("gpt-audio-mini", None, "", 0.60, None, 2.40),
    ("gpt-4o-audio-preview", None, "", 2.50, None, 10.00),
    ("gpt-4o-mini-audio-preview", None, "", 0.15, None, 0.60),
    ("o1", None, "", 15.00, 7.50, 60.00),
    ("o1-pro", None, "", 150.00, None, 600.00),
    ("o3-pro", None, "", 20.00, None, 80.00),
    ("o3", None, "", 2.00, 0.50, 8.00),
    ("o3-deep-research", None, "", 10.00, 2.50, 40.00),
    ("o4-mini", None, "", 1.10, 0.275, 4.40),
    ("o4-mini-deep-research", None, "", 2.00, 0.50, 8.00),
    ("o3-mini", None, "", 1.10, 0.55, 4.40),
    ("o1-mini", None, "", 1.10, 0.55, 4.40),
    ("gpt-5.1-codex-mini", None, "", 0.25, 0.025, 2.00),
    ("codex-mini-latest", None, "", 1.50, 0.375, 6.00),
    ("gpt-5-search-api", None, "", 1.25, 0.125, 10.00),
    ("gpt-4o-mini-search-preview", None, "", 0.15, None, 0.60),
    ("gpt-4o-search-preview", None, "", 2.50, None, 10.00),
    ("computer-use-preview", None, "", 3.00, None, 12.00),
    ("gpt-image-1.5", None, "", 5.00, 1.25, 10.00),
    ("chatgpt-image-latest", None, "", 5.00, 1.25, 10.00),
    ("gpt-image-1", None, "", 5.00, 1.25, None),
    ("gpt-image-1-mini", None, "", 2.00, 0.20, None),
]


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    db_path = project_root / "data" / "system_metrics.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
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
            MODEL_COSTS,
        )
        conn.commit()
    print(f"Metrics database initialized at {db_path}")


if __name__ == "__main__":
    main()
