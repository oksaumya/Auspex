"""Single ChatGroq factory shared by every reviewer agent."""
import logging
from typing import Optional

from core.config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE, has_groq_key

logger = logging.getLogger("LLM")

_llm = None


def build_llm():
    """Returns a configured ChatGroq client, or None when no API key is set.

    The result is memoized so a single client is reused across the pipeline.
    Callers fall back to deterministic heuristics when this returns None.
    """
    global _llm
    if _llm is not None:
        return _llm
    if not has_groq_key():
        return None
    try:
        from langchain_groq import ChatGroq

        _llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=GROQ_TEMPERATURE,
        )
        logger.info("ChatGroq client initialized (model=%s).", GROQ_MODEL)
        return _llm
    except Exception as exc:
        logger.error("Failed to initialize ChatGroq: %s", exc)
        return None
