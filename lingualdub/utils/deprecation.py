# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Deprecation utilities — PEV-002.

Provides ``@deprecated`` decorator for functions, classes, and methods that
emits ``DeprecationWarning`` with a standardized message.

Example:
    from lingualdub.utils.deprecation import deprecated

    @deprecated("Use new_func instead.", replacement="new_func", since="0.2.0")
    def old_func():
        pass

    old_func()  # warns: [DEPRECATED since v0.2.0] old_func is deprecated. Use new_func instead. Reason: Use new_func instead.

Warnings are suppressable via standard ``warnings`` filters:

    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["deprecated"]

T = TypeVar("T")


def _format_message(symbol: str, reason: str, replacement: str | None, since: str) -> str:
    since_part = f" since v{since}" if since else ""
    base = f"[DEPRECATED{since_part}] {symbol} is deprecated."
    if replacement:
        base += f" Use {replacement} instead."
    if reason:
        base += f" Reason: {reason}"
    return base


def deprecated(
    reason: str = "",
    *,
    replacement: str | None = None,
    since: str = "",
) -> Callable[[T], T]:
    """Decorator to mark a function, class, or method as deprecated.

    Args:
        reason: Human-readable reason for deprecation.
        replacement: Name of the replacement symbol, if any.
        since: Version string since when deprecation started (e.g. ``"0.2.0"``).

    Returns:
        Decorator that wraps the target and emits ``DeprecationWarning`` on use.

    The decorator works for functions, classes (wraps ``__init__``/``__new__``),
    and methods. The warning message is standardized:

        ``"[DEPRECATED since v{since}] {symbol} is deprecated. Use {replacement} instead. Reason: {reason}"``

    Warnings use ``stacklevel=2`` so the caller's location is reported, and are
    of category ``DeprecationWarning`` so they can be filtered via
    ``warnings.filterwarnings``.
    """

    def decorator(obj: T) -> T:
        symbol = getattr(obj, "__qualname__", getattr(obj, "__name__", str(obj)))

        if isinstance(obj, type):
            # Class deprecation — wrap __init__ to warn on instantiation
            original_init = obj.__init__  # type: ignore[assignment]

            @functools.wraps(original_init)  # type: ignore[arg-type]
            def warned_init(self: Any, *args: Any, **kwargs: Any) -> None:
                msg = _format_message(symbol, reason, replacement, since)
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
                return original_init(self, *args, **kwargs)  # type: ignore[misc]

            obj.__init__ = warned_init  # type: ignore[method-assign]
            # Also set a marker for testing
            try:
                obj._lingualdub_deprecated = True  # type: ignore[attr-defined]
                obj._lingualdub_deprecation_info = (reason, replacement, since)  # type: ignore[attr-defined]
            except Exception:
                pass
            return obj  # type: ignore[return-value]

        elif callable(obj):
            # Function / method
            @functools.wraps(obj)  # type: ignore[arg-type]
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                msg = _format_message(symbol, reason, replacement, since)
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
                return obj(*args, **kwargs)  # type: ignore[misc]

            # Markers
            try:
                wrapper._lingualdub_deprecated = True  # type: ignore[attr-defined]
                wrapper._lingualdub_deprecation_info = (reason, replacement, since)  # type: ignore[attr-defined]
            except Exception:
                pass
            return wrapper  # type: ignore[return-value]
        else:
            # Not callable/class — return as is
            return obj

    # Support usage as @deprecated without parentheses: @deprecated
    # In that case, the first argument is the function itself
    if callable(reason) and not isinstance(reason, str):
        # Called as @deprecated without args, reason is actually the function
        func = reason  # type: ignore[assignment]
        reason = ""
        return decorator(func)  # type: ignore[return-value]

    return decorator
