"""Result types returned by reviewer agents (so callers can aggregate usage)."""
from typing import List, NamedTuple

from core.usage import LLMUsage, ZERO_USAGE
from models.schemas import Issue


class ReviewerResult(NamedTuple):
    issues: List[Issue]
    usage: LLMUsage = ZERO_USAGE
