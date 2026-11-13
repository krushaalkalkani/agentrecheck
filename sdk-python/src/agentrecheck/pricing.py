"""Per-model token prices (USD per 1M tokens) used to estimate cost.

Prices change. Treat the table as a best-effort default and override it with
``register_price`` for anything that matters to your budget assertions.
"""

from __future__ import annotations

# model prefix -> (input $/1M, output $/1M)
_PRICES: dict[str, tuple[float, float]] = {
    # OpenAI (approximate list prices)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (1.25, 10.00),
    "o4-mini": (1.10, 4.40),
    "o3": (2.00, 8.00),
    # Anthropic
    "claude-fable-5-2": (8.00, 40.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.00, 5.00),
}


def register_price(model: str, input_per_million: float, output_per_million: float) -> None:
    """Add or override the price for a model (matched by prefix)."""
    _PRICES[model] = (input_per_million, output_per_million)


def price_for(model: str) -> tuple[float, float] | None:
    best: str | None = None
    for prefix in _PRICES:
        if model.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    return _PRICES[best] if best else None


def cost_for(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimated cost in USD. Unknown models cost 0.0."""
    price = price_for(model)
    if price is None:
        return 0.0
    cost = (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000
    return round(cost, 8)
