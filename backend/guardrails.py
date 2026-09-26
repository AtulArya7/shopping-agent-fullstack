"""Deterministic input guardrails that run before the shopping agent."""

import re
from dataclasses import dataclass

from database import product_vocabulary


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str


SHOPPING_TERMS = {
    "buy", "browse", "catalog", "checkout", "compare", "cost", "deal",
    "discount", "find", "item", "order", "organic", "price", "product",
    "purchase", "rating", "recommend", "review", "shop", "shopping",
    "stock", "store", "under", "available", "cheaper", "expensive",
    "ordered", "orders", "history", "spent", "spending", "reorder",
    "remember", "preference", "preferences", "prefer", "always", "budget",
}

FOLLOW_UP_TERMS = {
    "yes", "no", "okay", "ok", "sure", "first", "second", "third",
    "one", "two", "three", "it", "that", "this", "those", "proceed",
}

REJECTION_MESSAGE = (
    "I can only help with shopping tasks for this store, such as browsing "
    "products, comparing prices or ratings, and placing an order."
)


def check_shopping_message(message: str, has_history: bool = False) -> GuardrailResult:
    """Allow store/shopping requests and contextual shopping follow-ups."""
    normalized = message.strip().lower()
    if not normalized:
        return GuardrailResult(False, "empty message")

    words = set(re.findall(r"[a-z0-9]+", normalized))
    if words & SHOPPING_TERMS:
        return GuardrailResult(True, "shopping term")

    if words & product_vocabulary():
        return GuardrailResult(True, "catalog term")

    if has_history and (words & FOLLOW_UP_TERMS or re.fullmatch(r"#?\d+", normalized)):
        return GuardrailResult(True, "shopping follow-up")

    return GuardrailResult(False, "off-topic message")
