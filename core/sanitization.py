"""Input sanitization helpers applied to webhook payloads and diffs."""
import logging

from core.config import MAX_DIFF_CHARS

logger = logging.getLogger("Sanitization")

INJECTION_KEYWORDS = (
    "ignore all previous",
    "ignore previous",
    "system override",
    "you must now",
    "forget what you",
    "disregard instructions",
    "override system prompt",
)


def detect_and_sterilize_injection(text: str) -> str:
    """Strips known prompt-injection phrases from user-supplied text."""
    lower_text = text.lower()
    for keyword in INJECTION_KEYWORDS:
        if keyword in lower_text:
            logger.warning("Prompt injection vector detected: %r. Sterilizing.", keyword)
            return f"[SECURITY WARN: Potential injection content sanitized]: {text.replace(keyword, '[STRIP]')}"
    return text


def sanitize_diff_content(content: str) -> str:
    """Clips overly large diffs so they never blow the LLM context window."""
    if len(content) > MAX_DIFF_CHARS:
        logger.warning("Diff content too large (%d chars). Truncating.", len(content))
        return content[:MAX_DIFF_CHARS] + "\n... [TRUNCATED FOR SECURITY] ..."
    return content
