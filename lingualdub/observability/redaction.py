# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Redaction filter for sensitive fields — PRO-005.

Scans log record fields and message against a configurable list of sensitive
field names and replaces values with ``[REDACTED]``.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["RedactionFilter"]

_DEFAULT_SENSITIVE_FIELDS = [
    "api_key",
    "access_token",
    "speaker_reference",
    "voice_path",
    "consent_record",
    "email",
]

_REDACTED = "[REDACTED]"


class RedactionFilter(logging.Filter):
    """Logging filter that redacts sensitive field values.

    Args:
        sensitive_fields: List of field names to redact. If None, uses default
            set from ``_DEFAULT_SENSITIVE_FIELDS``. The list is case-insensitive
            matched against record attributes and message content.
        extra_fields: Additional fields supplied at runtime (e.g. from
            ``FrameworkConfig.sensitive_fields``).
    """

    def __init__(
        self, sensitive_fields: list[str] | None = None, extra_fields: list[str] | None = None
    ):
        super().__init__()
        base = list(_DEFAULT_SENSITIVE_FIELDS)
        if sensitive_fields:
            base.extend(sensitive_fields)
        if extra_fields:
            base.extend(extra_fields)
        # Normalize to lower for case-insensitive matching, dedupe
        seen: set[str] = set()
        self.sensitive_fields: list[str] = []
        for f in base:
            low = f.lower()
            if low not in seen:
                seen.add(low)
                self.sensitive_fields.append(low)
        # Also keep original case for direct attribute redaction
        self._field_set = set(self.sensitive_fields)

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact attributes that match sensitive field names
        for key in list(record.__dict__.keys()):
            if key.lower() in self._field_set:
                record.__dict__[key] = _REDACTED
        # Redact message args if they contain sensitive field names
        # e.g. record.args may be dict or tuple
        if isinstance(record.args, dict):
            for k in list(record.args.keys()):
                if k.lower() in self._field_set:
                    record.args[k] = _REDACTED
        # Redact msg string if it contains sensitive patterns like "api_key=secret"
        msg = record.getMessage()
        lower_msg = msg.lower()
        redacted = False
        for field in self.sensitive_fields:
            if field in lower_msg:
                # Replace field value pattern: field=xxx or field: xxx or "field": "xxx"
                # Simplified: if field name appears, redact whole message value part
                # We replace any occurrence of field with field=[REDACTED] in msg
                # Instead of complex regex, just check if field in msg and value likely present, redact.
                # For test expectations, we ensure sensitive value not in output.
                # We'll scan for field and replace following value up to space/quote/comma
                import re

                pattern = re.compile(
                    rf'({re.escape(field)}\s*[:=]\s*)([^\s,\"\']+|"[^"]*"|\'[^\']*\')',
                    re.IGNORECASE,
                )
                new_msg, n = pattern.subn(rf"\1{_REDACTED}", msg)
                if n > 0:
                    msg = new_msg
                    redacted = True
        if redacted:
            # Override record.msg to redacted version and clear args to avoid double formatting
            record.msg = msg
            record.args = ()
        # Always allow record through (filter returns True)
        return True

    def redact_value(self, value: Any) -> Any:
        """Redact a single value if its key is sensitive (helper)."""
        return _REDACTED

    def is_sensitive(self, key: str) -> bool:
        return key.lower() in self._field_set
