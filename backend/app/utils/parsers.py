import json
import re
from typing import Any


def safe_json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def parse_bool(raw: str | None) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "y"}


def parse_float(raw: str | None, default: float = 0.0) -> float:
    if raw is None:
        return default
    text = str(raw).strip()
    if not text:
        return default
    text = text.replace("$", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return default


def parse_int(raw: str | None, default: int = 0) -> int:
    if raw is None:
        return default
    text = str(raw).strip()
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned
