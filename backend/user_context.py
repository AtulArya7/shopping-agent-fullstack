"""Trusted request context available to agent tools without model input."""

from contextvars import ContextVar


current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def require_context_user() -> int:
    user_id = current_user_id.get()
    if user_id is None:
        raise RuntimeError("This tool requires an authenticated user.")
    return user_id
