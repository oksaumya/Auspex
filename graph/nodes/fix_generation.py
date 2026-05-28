"""4. Fix Generation Node — turns each Issue into a Fix via LLM or heuristics."""
import logging
import uuid
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from core.llm import build_llm
from core.usage import LLMUsage, invoke_structured, merge
from graph.state import GraphState
from models.schemas import Fix, Issue, IssueType
from reviewers.prompts import FIX_GENERATION_PROMPT

logger = logging.getLogger("Node.FixGeneration")


class ProposedFixOutput(BaseModel):
    original_code: str = Field(description="The exact buggy section of code from the file")
    proposed_code: str = Field(description="The refactored, corrected code")
    explanation: str = Field(description="Brief explanation of why this fix is safe and optimal")


def _heuristic_fix(issue: Issue, fix_id: str) -> Fix:
    desc = issue.description.lower()
    if issue.type == IssueType.BUG and "float" in desc:
        original = "ratio = float(username)"
        proposed = """try:
        ratio = float(username)
    except ValueError:
        ratio = 0.0  # safe default fallback"""
        explanation = "Handles float conversion exceptions when the username is non-numeric."
    elif issue.type == IssueType.BUG:
        original = "def verify_login"
        proposed = "# Added input length checks\nif not username or len(username) > 100:\n    return False\n\ndef verify_login"
        explanation = "Adds input boundary constraints on the public function."
    elif issue.type == IssueType.SECURITY and "hardcoded" in desc:
        original = 'SECRET_KEY = "SUPER_SECRET_12345"'
        proposed = 'SECRET_KEY = __import__("os").getenv("APP_SECRET_KEY", "DEFAULT_FALLBACK_KEY")'
        explanation = "Loads the secret from an environment variable instead of hardcoding."
    elif issue.type == IssueType.SECURITY and ("md5" in desc or "weak cryptographic" in desc):
        original = """h = hashlib.md5()
    h.update(data.encode())
    return h.hexdigest()"""
        proposed = """h = hashlib.sha256()
    h.update(data.encode())
    return h.hexdigest()"""
        explanation = "Upgrades the weak MD5 hash to SHA256."
    elif issue.type == IssueType.SECURITY:
        original = "eval("
        proposed = "json.loads("
        explanation = "Replaces dynamic code evaluation with safe JSON parsing."
    elif issue.type == IssueType.PERFORMANCE and "nested loop" in desc:
        original = """results = []
    for r1 in records:
        for r2 in records:
            if r1 != r2:
                results.append((r1, r2))
    return results"""
        proposed = """# Optimized: only iterate unique pairs once
    results = []
    unique_records = list(set(records))
    for i, r1 in enumerate(unique_records):
        for r2 in unique_records[i+1:]:
            results.append((r1, r2))
            results.append((r2, r1))
    return results"""
        explanation = "Deduplicates inputs to reduce comparisons inside the nested loop."
    elif issue.type == IssueType.PERFORMANCE and "open(" in desc:
        original = '''f = open(filename, "r")
    content = f.read()
    return content'''
        proposed = '''with open(filename, "r") as f:
        content = f.read()
    return content'''
        explanation = "Wraps file I/O in a context manager to ensure the descriptor closes."
    else:
        original = "pass"
        proposed = "# Optimizations applied"
        explanation = "Proposed correction for identified issue."

    return Fix(
        id=fix_id,
        issue_id=issue.id,
        original_code=original,
        proposed_code=proposed,
        explanation=explanation,
    )


def fix_generation_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Fix Generation Node...")
    llm = build_llm()
    fixes: List[Fix] = []
    usages: List[LLMUsage] = []

    for issue in state["issues"]:
        fix_id = str(uuid.uuid4())

        if not llm:
            fixes.append(_heuristic_fix(issue, fix_id))
            continue

        file_info = next((f for f in state["changed_files"] if f["path"] == issue.file), None)
        file_content = file_info["content"] if file_info else ""

        prompt = FIX_GENERATION_PROMPT.format(
            file=issue.file,
            line=issue.line,
            type=issue.type,
            severity=issue.severity,
            description=issue.description,
            file_content=file_content,
        )
        try:
            parsed, usage = invoke_structured(llm, ProposedFixOutput, prompt)
            usages.append(usage)
            if parsed is None:
                logger.warning("Fix Generation returned no parsed result for issue %s. Falling back.", issue.id)
                fixes.append(_heuristic_fix(issue, fix_id))
                continue
            fixes.append(Fix(
                id=fix_id,
                issue_id=issue.id,
                original_code=parsed.original_code,
                proposed_code=parsed.proposed_code,
                explanation=parsed.explanation,
            ))
        except Exception as exc:
            logger.error("Fix Generation LLM call failed: %s. Falling back to heuristic.", exc)
            fixes.append(_heuristic_fix(issue, fix_id))

    aggregate = merge(usages)
    return {
        "fixes": fixes,
        "status": "fixed",
        "cost": (state.get("cost", 0.0) or 0.0) + aggregate.cost_usd,
        "tokens_used": (state.get("tokens_used", 0) or 0) + aggregate.total_tokens,
    }
