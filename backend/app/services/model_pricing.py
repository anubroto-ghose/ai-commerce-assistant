from dataclasses import dataclass


TOKENS_PER_MILLION = 1_000_000
GPT_54_CONTEXT_THRESHOLD = 272_000


@dataclass(frozen=True)
class ModelPricing:
    model_key: str
    input_cost_per_million: float
    cached_input_cost_per_million: float | None
    output_cost_per_million: float | None
    context_threshold: int | None = None
    note: str = ""


MODEL_PRICING_TABLE: tuple[ModelPricing, ...] = (
    ModelPricing("gpt-5.4", 2.50, 0.25, 15.00, GPT_54_CONTEXT_THRESHOLD, "<272K context length"),
    ModelPricing("gpt-5.4", 5.00, 0.50, 22.50, GPT_54_CONTEXT_THRESHOLD, ">272K context length"),
    ModelPricing("gpt-5.4-pro", 30.00, None, 180.00, GPT_54_CONTEXT_THRESHOLD, "<272K context length"),
    ModelPricing("gpt-5.4-pro", 60.00, None, 270.00, GPT_54_CONTEXT_THRESHOLD, ">272K context length"),
    ModelPricing("gpt-5.2", 1.75, 0.175, 14.00),
    ModelPricing("gpt-5.1", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5-mini", 0.25, 0.025, 2.00),
    ModelPricing("gpt-5-nano", 0.05, 0.005, 0.40),
    ModelPricing("gpt-5.3-chat-latest", 1.75, 0.175, 14.00),
    ModelPricing("gpt-5.2-chat-latest", 1.75, 0.175, 14.00),
    ModelPricing("gpt-5.1-chat-latest", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5-chat-latest", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5.3-codex", 1.75, 0.175, 14.00),
    ModelPricing("gpt-5.2-codex", 1.75, 0.175, 14.00),
    ModelPricing("gpt-5.1-codex-max", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5.1-codex", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5-codex", 1.25, 0.125, 10.00),
    ModelPricing("gpt-5.2-pro", 21.00, None, 168.00),
    ModelPricing("gpt-5-pro", 15.00, None, 120.00),
    ModelPricing("gpt-4.1", 2.00, 0.50, 8.00),
    ModelPricing("gpt-4.1-mini", 0.40, 0.10, 1.60),
    ModelPricing("gpt-4.1-nano", 0.10, 0.025, 0.40),
    ModelPricing("gpt-4o", 2.50, 1.25, 10.00),
    ModelPricing("gpt-4o-2024-05-13", 5.00, None, 15.00),
    ModelPricing("gpt-4o-mini", 0.15, 0.075, 0.60),
    ModelPricing("gpt-realtime", 4.00, 0.40, 16.00),
    ModelPricing("gpt-realtime-1.5", 4.00, 0.40, 16.00),
    ModelPricing("gpt-realtime-mini", 0.60, 0.06, 2.40),
    ModelPricing("gpt-4o-realtime-preview", 5.00, 2.50, 20.00),
    ModelPricing("gpt-4o-mini-realtime-preview", 0.60, 0.30, 2.40),
    ModelPricing("gpt-audio", 2.50, None, 10.00),
    ModelPricing("gpt-audio-1.5", 2.50, None, 10.00),
    ModelPricing("gpt-audio-mini", 0.60, None, 2.40),
    ModelPricing("gpt-4o-audio-preview", 2.50, None, 10.00),
    ModelPricing("gpt-4o-mini-audio-preview", 0.15, None, 0.60),
    ModelPricing("o1", 15.00, 7.50, 60.00),
    ModelPricing("o1-pro", 150.00, None, 600.00),
    ModelPricing("o3-pro", 20.00, None, 80.00),
    ModelPricing("o3", 2.00, 0.50, 8.00),
    ModelPricing("o3-deep-research", 10.00, 2.50, 40.00),
    ModelPricing("o4-mini", 1.10, 0.275, 4.40),
    ModelPricing("o4-mini-deep-research", 2.00, 0.50, 8.00),
    ModelPricing("o3-mini", 1.10, 0.55, 4.40),
    ModelPricing("o1-mini", 1.10, 0.55, 4.40),
    ModelPricing("gpt-5.1-codex-mini", 0.25, 0.025, 2.00),
    ModelPricing("codex-mini-latest", 1.50, 0.375, 6.00),
    ModelPricing("gpt-5-search-api", 1.25, 0.125, 10.00),
    ModelPricing("gpt-4o-mini-search-preview", 0.15, None, 0.60),
    ModelPricing("gpt-4o-search-preview", 2.50, None, 10.00),
    ModelPricing("computer-use-preview", 3.00, None, 12.00),
    ModelPricing("gpt-image-1.5", 5.00, 1.25, 10.00),
    ModelPricing("chatgpt-image-latest", 5.00, 1.25, 10.00),
    ModelPricing("gpt-image-1", 5.00, 1.25, None),
    ModelPricing("gpt-image-1-mini", 2.00, 0.20, None),
)


def resolve_model_pricing(model_name: str, input_tokens: int) -> ModelPricing | None:
    direct = [entry for entry in MODEL_PRICING_TABLE if entry.model_key == model_name]
    if not direct:
        return None
    if model_name in {"gpt-5.4", "gpt-5.4-pro"}:
        above_threshold = input_tokens > GPT_54_CONTEXT_THRESHOLD
        for entry in direct:
            if above_threshold and entry.note.startswith(">"):
                return entry
            if not above_threshold and entry.note.startswith("<"):
                return entry
    return direct[0]
