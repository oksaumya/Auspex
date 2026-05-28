"""Issue post-processing: enforce per-agent category scope and dedupe results."""
import re
from typing import Iterable, List

from models.schemas import Issue, IssueType


# Keyword fingerprints used to filter LLM drift. If a Performance agent returns
# something that mentions "hardcoded secret", we drop it.
_CATEGORY_KEYWORDS = {
    IssueType.BUG: (
        "off-by-one", "off by one", "null", "none deref", "nonetype",
        "race condition", "exception", "except clause", "try/except",
        "wrong return", "default argument", "logic", "loop bound",
        "type coercion", "valueerror", "indexerror", "keyerror",
        "edge case", "boundary",
    ),
    IssueType.SECURITY: (
        "secret", "password", "credential", "token", "api key", "api_key",
        "injection", "xss", "csrf", "ssrf", "owasp", "auth",
        "crypto", "md5", "sha1", "ecb", "iv ",
        "pickle", "yaml.load", "deserialization",
        "traversal", "path injection", "eval(", "exec(",
        "vulnerability", "ssl", "tls", "certificate",
    ),
    IssueType.PERFORMANCE: (
        "n^2", "n*n", "o(n^", "quadratic", "complexity",
        "n+1", "nested loop", "hot loop", "recompute",
        "memory leak", "unbounded", "cache", "allocate",
        "context manager", "with statement", "file handle",
        "descriptor", "blocking", "synchronous",
        "lookup", "scan", "index",
    ),
}


def _matches_category(description: str, category: IssueType) -> bool:
    text = description.lower()
    keywords = _CATEGORY_KEYWORDS.get(category, ())
    # Empty rubric → accept (defensive default).
    if not keywords:
        return True
    return any(kw in text for kw in keywords)


def filter_to_category(issues: Iterable[Issue], category: IssueType) -> List[Issue]:
    """Drops issues whose description doesn't match the agent's category."""
    return [i for i in issues if _matches_category(i.description, category)]


_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(description: str) -> str:
    """Coarse normalization: lowercase + first 8 alphanumeric tokens."""
    tokens = _WORD_RE.findall(description.lower())
    return " ".join(tokens[:8])


def deduplicate(issues: List[Issue]) -> List[Issue]:
    """Removes near-duplicate issues across agents.

    Two issues are considered duplicates when they share the same file and
    the first 8 normalized tokens of their description. When duplicates exist,
    the one with the highest severity is kept.
    """
    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    seen: dict[tuple[str, str], Issue] = {}
    for issue in issues:
        key = (issue.file, _normalize(issue.description))
        existing = seen.get(key)
        if existing is None:
            seen[key] = issue
            continue
        if severity_rank.get(issue.severity.value, 0) > severity_rank.get(existing.severity.value, 0):
            seen[key] = issue
    return list(seen.values())
