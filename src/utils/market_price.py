"""
Market Price Extraction Utility

The Kalshi v2 API returns yes_bid/yes_ask/no_bid/no_ask fields,
NOT yes_price/no_price. This utility provides consistent price
extraction from API responses to avoid defaulting to 50 cents.
"""

from typing import Dict, Any, Optional, Tuple


def get_market_price_cents(market_info: Dict[str, Any], side: str = "yes") -> int:
    """
    Extract the best available price in CENTS from a Kalshi API market response.

    Uses the following priority:
    1. Mid-price from bid/ask (most accurate)
    2. Ask price only (if no bid)
    3. Bid price only (if no ask)
    4. last_price (last traded price)
    5. previous_yes_price / previous_price (historical fallback)
    6. Returns 0 if no price data available (caller must handle)

    Args:
        market_info: The market dict from Kalshi API (the nested 'market' object).
        side: "yes" or "no"

    Returns:
        Price in cents (0-99), or 0 if no price data available.
    """
    if side.lower() == "yes":
        bid = market_info.get('yes_bid') or 0
        ask = market_info.get('yes_ask') or 0
    else:
        bid = market_info.get('no_bid') or 0
        ask = market_info.get('no_ask') or 0

    # Mid-price from bid/ask
    if bid > 0 and ask > 0:
        return (bid + ask) // 2
    elif ask > 0:
        return ask
    elif bid > 0:
        return bid

    # Fallback to last_price
    last_price = market_info.get('last_price') or 0
    if last_price > 0:
        return last_price

    # Fallback to previous price fields
    if side.lower() == "yes":
        prev = market_info.get('previous_yes_price') or 0
    else:
        prev = market_info.get('previous_no_price') or 0
    if prev > 0:
        return prev

    prev_generic = market_info.get('previous_price') or 0
    if prev_generic > 0:
        if side.lower() == "yes":
            return prev_generic
        else:
            return max(0, 100 - prev_generic)

    return 0


def get_market_price_dollars(market_info: Dict[str, Any], side: str = "yes") -> float:
    """
    Extract the best available price in DOLLARS from a Kalshi API market response.

    Args:
        market_info: The market dict from Kalshi API.
        side: "yes" or "no"

    Returns:
        Price as a float (0.0-0.99), or 0.0 if no price data available.
    """
    cents = get_market_price_cents(market_info, side)
    return cents / 100.0


def get_both_prices_cents(market_info: Dict[str, Any]) -> Tuple[int, int]:
    """
    Extract both YES and NO prices in cents.

    Returns:
        (yes_price_cents, no_price_cents)
    """
    yes_cents = get_market_price_cents(market_info, "yes")
    no_cents = get_market_price_cents(market_info, "no")

    # If we have one price but not the other, derive it (YES + NO = 100 on Kalshi)
    if yes_cents > 0 and no_cents == 0:
        no_cents = max(1, 100 - yes_cents)
    elif no_cents > 0 and yes_cents == 0:
        yes_cents = max(1, 100 - no_cents)

    return yes_cents, no_cents


def get_both_prices_dollars(market_info: Dict[str, Any]) -> Tuple[float, float]:
    """
    Extract both YES and NO prices in dollars.

    Returns:
        (yes_price_dollars, no_price_dollars)
    """
    yes_cents, no_cents = get_both_prices_cents(market_info)
    return yes_cents / 100.0, no_cents / 100.0


def has_valid_prices(market_info: Dict[str, Any]) -> bool:
    """
    Check if a market has any valid price data.

    Returns:
        True if at least one price field has a nonzero value.
    """
    yes_cents, no_cents = get_both_prices_cents(market_info)
    return yes_cents > 0 or no_cents > 0
