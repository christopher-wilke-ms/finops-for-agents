"""
Token pricing lookup via the Azure Retail Prices API.

Resolves the real USD price per token for a given model and caches the result
in-process, so the API is called at most once per model per TTL window.
"""

import os
import time
from typing import NamedTuple

import requests

PRICING_API = "https://prices.azure.com/api/retail/prices"
PRICING_API_VERSION = "2023-01-01-preview"

REGION = os.getenv("PRICING_REGION", "swedencentral")
CACHE_TTL_SECONDS = int(os.getenv("PRICING_CACHE_TTL_SECONDS", "86400"))


class TokenPrices(NamedTuple):
    """USD price for a single token of each billable type."""

    input: float
    cached_input: float
    output: float


# Model id -> (input, cached input, output) meters in the retail price catalogue.
# The Responses API reports the *deployment* name, so this assumes deployment name
# == model name and a GlobalStandard SKU - both set that way in infra/main.tf.
# Meter naming differs per model family, so each model needs an explicit entry.
METERS = {
    "gpt-5-mini": (
        "GPT 5 Mini Inpt Glbl 1M Tokens",
        "GPT 5 Mini cchd Inpt Glbl 1M Tokens",
        "GPT 5 Mini outpt Glbl 1M Tokens",
    ),
}

# Per-token prices used when the model is unmapped or the API is unreachable.
FALLBACK = {
    "gpt-5-mini": TokenPrices(0.25 / 1e6, 0.025 / 1e6, 2.00 / 1e6),
}

NO_PRICES = TokenPrices(0.0, 0.0, 0.0)

_cache: dict[str, tuple[float, TokenPrices]] = {}


def get_token_prices(model_id: str) -> TokenPrices:
    """
    Return the per-token USD prices for a model.

    Args:
        model_id: Model identifier as reported by Foundry, e.g. "gpt-5-mini"

    Returns:
        TokenPrices. Falls back to static values if the lookup fails, so this
        never raises into the request path.
    """
    cached = _cache.get(model_id)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    # Unmapped models cost nothing to re-check, and staying loud beats silently
    # reporting $0 for real token usage.
    if model_id not in METERS:
        print(f"[PRICING] No meter mapping for model '{model_id}' - cost will be reported as $0")
        return FALLBACK.get(model_id, NO_PRICES)

    if cached:
        age_hours = (time.time() - cached[0]) / 3600
        print(f"[PRICING] Cached prices for '{model_id}' expired after {age_hours:.1f}h, refreshing")

    prices = _fetch_prices(model_id)
    if prices is None:
        prices = FALLBACK.get(model_id, NO_PRICES)
        print(
            f"[PRICING] Using static fallback prices for '{model_id}': "
            f"input ${prices.input:.9f}, cached input ${prices.cached_input:.9f}, "
            f"output ${prices.output:.9f} per token"
        )

    _cache[model_id] = (time.time(), prices)
    print(f"[PRICING] Cached prices for '{model_id}' for the next {CACHE_TTL_SECONDS / 3600:.0f}h")
    return prices


def _fetch_prices(model_id: str) -> TokenPrices | None:
    """
    Fetch the input, cached input and output meter prices from the Azure Retail
    Prices API.

    Returns:
        TokenPrices, or None if the lookup fails.

    Internal function - called by get_token_prices()
    """
    meters = METERS[model_id]

    try:
        meter_filter = " or ".join(f"meterName eq '{meter}'" for meter in meters)
        query = (
            f"serviceName eq 'Foundry Models' and armRegionName eq '{REGION}' "
            f"and ({meter_filter})"
        )

        print(f"[PRICING] Fetching prices for '{model_id}' in {REGION} from {PRICING_API}")
        print(f"[PRICING]   filter: {query}")

        started = time.monotonic()
        response = requests.get(
            PRICING_API,
            params={"api-version": PRICING_API_VERSION, "$filter": query},
            timeout=5,
        )
        elapsed_ms = (time.monotonic() - started) * 1000
        print(f"[PRICING]   HTTP {response.status_code} in {elapsed_ms:.0f} ms")
        response.raise_for_status()

        items = response.json().get("Items", [])
        print(f"[PRICING]   {len(items)} of {len(meters)} expected meter(s) returned")
        items_by_meter = {item["meterName"]: item for item in items}

        prices = []
        for field, meter in zip(TokenPrices._fields, meters):
            item = items_by_meter.get(meter)
            if item is None:
                raise LookupError(f"meter '{meter}' missing from the API response")
            # unitOfMeasure is "1M" or "1K" depending on the model
            divisor = 1e6 if item["unitOfMeasure"].startswith("1M") else 1e3
            per_token = item["retailPrice"] / divisor
            print(
                f"[PRICING]   {field:12} '{meter}' = ${item['retailPrice']} per "
                f"{item['unitOfMeasure']} -> ${per_token:.9f}/token"
            )
            prices.append(per_token)

        return TokenPrices(*prices)

    except Exception as err:
        print(f"[PRICING] Lookup failed for '{model_id}': {type(err).__name__}: {err}")
        return None
