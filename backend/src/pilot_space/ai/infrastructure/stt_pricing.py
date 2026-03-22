"""Duration-based pricing for Speech-to-Text providers.

Separated from cost_tracker.py to keep modules under the 700-line limit.
Pricing is per-minute of audio processed.  BYOK — actual cost depends
on the user's plan; these are reasonable defaults.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Duration-based pricing per minute (STT providers)
# Structure: {provider: {model: cost_per_minute_usd}}
STT_PRICING_PER_MINUTE: Final[dict[str, dict[str, Decimal]]] = {
    "elevenlabs": {
        "scribe_v2": Decimal("0.012"),
        "scribe_v2_realtime": Decimal("0.012"),
    },
}


def calculate_stt_cost(
    provider: str,
    model: str,
    duration_seconds: float,
) -> float:
    """Calculate cost for STT usage based on audio duration.

    Args:
        provider: STT provider (e.g. ``"elevenlabs"``).
        model: Model identifier (e.g. ``"scribe_v2"``).
        duration_seconds: Audio duration in seconds.

    Returns:
        Cost in USD as float.  Returns ``0.0`` for unknown providers/models
        (logged as warning) so cost tracking never crashes callers.
    """
    provider_pricing = STT_PRICING_PER_MINUTE.get(provider)
    if provider_pricing is None:
        logger.warning("stt_cost_unknown_provider", provider=provider, model=model)
        return 0.0

    price_per_minute = provider_pricing.get(model)
    if price_per_minute is None:
        logger.warning(
            "stt_cost_unknown_model",
            provider=provider,
            model=model,
            supported=list(provider_pricing.keys()),
        )
        return 0.0

    duration_minutes = Decimal(str(duration_seconds)) / 60
    return float(duration_minutes * price_per_minute)


__all__ = [
    "STT_PRICING_PER_MINUTE",
    "calculate_stt_cost",
]
