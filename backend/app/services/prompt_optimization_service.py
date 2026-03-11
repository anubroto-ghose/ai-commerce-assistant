from dataclasses import dataclass

from app.utils.config import LLMLINGUA_ENABLED

try:
    from llmlingua import PromptCompressor
except Exception:  # pragma: no cover
    PromptCompressor = None


@dataclass(frozen=True)
class CompressionResult:
    compressed_text: str
    original_chars: int
    compressed_chars: int
    strategy: str


class PromptOptimizationService:
    def __init__(self) -> None:
        self.available = bool(LLMLINGUA_ENABLED and PromptCompressor is not None)
        self.compressor = None

    def compress(self, system_prompt: str, retrieved_context: str) -> CompressionResult:
        combined = "\n\n".join(part for part in [system_prompt.strip(), retrieved_context.strip()] if part.strip())
        original_chars = len(combined)
        if not combined:
            return CompressionResult("", 0, 0, "empty")

        if self.available:
            self._ensure_compressor()
        if self.available and self.compressor is not None:
            compressed = self._compress_with_llmlingua(combined)
            if compressed:
                return CompressionResult(
                    compressed_text=compressed,
                    original_chars=original_chars,
                    compressed_chars=len(compressed),
                    strategy="llmlingua",
                )

        heuristic = self._heuristic_compress(combined)
        return CompressionResult(
            compressed_text=heuristic,
            original_chars=original_chars,
            compressed_chars=len(heuristic),
            strategy="heuristic",
        )

    def _ensure_compressor(self) -> None:
        if self.compressor is not None or not self.available:
            return
        try:
            self.compressor = PromptCompressor()
        except Exception:
            self.available = False
            self.compressor = None

    def _compress_with_llmlingua(self, combined: str) -> str:
        candidates = (
            {"instruction": "Retain policy rules, product facts, and privacy constraints.", "rate": 0.6},
            {"instruction": "Retain policy rules, product facts, and privacy constraints.", "target_token": 512},
            {"rate": 0.6},
        )
        for kwargs in candidates:
            try:
                result = self.compressor.compress_prompt(combined, **kwargs)
                if isinstance(result, dict):
                    text = result.get("compressed_prompt") or result.get("prompt")
                    if text:
                        return str(text)
                if isinstance(result, str):
                    return result
            except TypeError:
                continue
            except Exception:
                break
        return ""

    @staticmethod
    def _heuristic_compress(text: str) -> str:
        lines = []
        seen: set[str] = set()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line in seen:
                continue
            seen.add(line)
            lines.append(line)
        compact = " ".join(lines)
        if len(compact) > 1600:
            compact = compact[:1600]
        return compact
