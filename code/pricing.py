"""
Token pricing lookup via the Azure Retail Prices API.

Resolves the real USD price per token for a given model and caches the result
in-process, so the API is called at most once per model per TTL window.
"""

import os
import time
import requests

PRICING_API = "https://prices.azure.com/api/retail/prices"
PRICING_API_VERSION = "2023-01-01-preview"

REGION = os.getenv("PRICING_REGION", "swedencentral")
CACHE_TTL_SECONDS = int(os.getenv("PRICING_CACHE_TTL_SECONDS", "86400"))

# Model id -> (input meter, output meter) in the retail price catalogue.
# The Responses API reports the *deployment* name, so this assumes deployment name
# == model name and a GlobalStandard SKU - both set that way in infra/main.tf.
# Meter naming differs per model family, so each model needs an explicit entry.
METERS = {
    "gpt-5-mini": ("GPT 5 Mini Inpt Glbl 1M Tokens", "GPT 5 Mini outpt Glbl 1M Tokens"),
}

# Per-token prices used when the model is unmapped or the API is unreachable.
FALLBACK = {
    "gpt-5-mini": (0.25 / 1e6, 2.00 / 1e6),
}

_cache: dict[str, tuple[float, tuple[float, float]]] = {}


def get_token_prices(model_id: str) -> tuple[float, float]:
    """
    Return (input_price, output_price) per single token in USD.

    Args:
        model_id: Model identifier as reported by Foundry, e.g. "gpt-5-mini"

    Returns:
        Tuple of per-token prices. Falls back to static values if the lookup
        fails, so this never raises into the request path.
    """
    cached = _cache.get(model_id)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    # Unmapped models cost nothing to re-check, and staying loud beats silently
    # reporting $0 for real token usage.
    if model_id not in METERS:
        print(f"[PRICING] No meter mapping for model '{model_id}' - cost will be reported as $0")
        return FALLBACK.get(model_id, (0.0, 0.0))

    prices = _fetch_prices(model_id) or FALLBACK.get(model_id, (0.0, 0.0))
    _cache[model_id] = (time.time(), prices)
    return prices


def _fetch_prices(model_id: str) -> tuple[float, float] | None:
    """
    Fetch input and output meter prices from the Azure Retail Prices API.

    Returns:
        Tuple of per-token prices, or None if the lookup fails.

    Internal function - called by get_token_prices()
    """
    meters = METERS[model_id]

    try:
        query = (
            f"serviceName eq 'Foundry Models' and armRegionName eq '{REGION}' "
            f"and (meterName eq '{meters[0]}' or meterName eq '{meters[1]}')"
        )
        response = requests.get(
            PRICING_API,
            params={"api-version": PRICING_API_VERSION, "$filter": query},
            timeout=5,
        )
        response.raise_for_status()

        items_by_meter = {item["meterName"]: item for item in response.json().get("Items", [])}

        prices = []
        for meter in meters:
            item = items_by_meter[meter]
            # unitOfMeasure is "1M" or "1K" depending on the model
            divisor = 1e6 if item["unitOfMeasure"].startswith("1M") else 1e3
            prices.append(item["retailPrice"] / divisor)

        print(f"[PRICING] {model_id} @ {REGION}: input ${prices[0]:.9f}/token, output ${prices[1]:.9f}/token")
        return prices[0], prices[1]

    except Exception as err:
        print(f"[PRICING] Lookup failed for '{model_id}': {err}")
        return None
