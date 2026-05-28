"""Deterministic fallback reviewer used when no LLM key is configured."""
from typing import List

from models.schemas import Issue, IssueType, Severity


def _line_of(content: str, needle: str, default: int = 1) -> int:
    pos = content.find(needle)
    if pos < 0:
        return default
    return max(1, pos // 40 + 1)


def run_mock_review(filepath: str, content: str, patch: str, agent_type: IssueType) -> List[Issue]:
    """Generates realistic-looking issues from simple substring heuristics."""
    issues: List[Issue] = []

    if agent_type == IssueType.BUG:
        if "except:" in content or "except Exception:" in content:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "except"),
                type=IssueType.BUG,
                severity=Severity.MEDIUM,
                description="Bare 'except:' or 'except Exception:' catches all errors without logging, potentially masking severe application bugs.",
            ))
        if "assert " in content:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "assert"),
                type=IssueType.BUG,
                severity=Severity.LOW,
                description="Use of assertions in production code. Assertions are ignored if python is compiled with optimization (-O) flag.",
            ))
        if "float(" in content and "try:" not in content:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "float("),
                type=IssueType.BUG,
                severity=Severity.HIGH,
                description="Parsing string float directly without a try-except block could result in unhandled ValueError if input is not formatted.",
            ))

    elif agent_type == IssueType.SECURITY:
        lower = content.lower()
        if any(kw in lower for kw in ("secret", "password", "api_key", "token")):
            issues.append(Issue(
                file=filepath,
                line=1,
                type=IssueType.SECURITY,
                severity=Severity.CRITICAL,
                description="Potential hardcoded secret or API credential detected in code. Secrets must be loaded securely via environment variables.",
            ))
        if "md5" in lower or "sha1" in lower:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "md5"),
                type=IssueType.SECURITY,
                severity=Severity.HIGH,
                description="Use of weak cryptographic hashing algorithm (MD5 or SHA1). Replace with SHA256 or bcrypt for password hashing.",
            ))
        if "eval(" in content or "exec(" in content:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "eval("),
                type=IssueType.SECURITY,
                severity=Severity.CRITICAL,
                description="Critical code-injection vulnerability: dynamic code execution using 'eval' or 'exec' with untrusted input.",
            ))

    elif agent_type == IssueType.PERFORMANCE:
        if "for " in content and "for " in content[content.find("for ") + 4:]:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "for "),
                type=IssueType.PERFORMANCE,
                severity=Severity.MEDIUM,
                description="Nested loops detected (O(N^2) complexity). Could cause severe CPU bottlenecks for large datasets.",
            ))
        if "open(" in content and "with " not in content:
            issues.append(Issue(
                file=filepath,
                line=_line_of(content, "open("),
                type=IssueType.PERFORMANCE,
                severity=Severity.HIGH,
                description="File resource opened without 'with' statement context manager. Could result in unclosed file descriptors/leaks.",
            ))

    if not issues:
        fallback_by_type = {
            IssueType.BUG: (10, Severity.LOW, "Missing edge case handling for empty inputs in public function definitions."),
            IssueType.SECURITY: (5, Severity.MEDIUM, "Missing input validation/sanitization in main endpoint entry point."),
            IssueType.PERFORMANCE: (15, Severity.LOW, "Consider caching repeated computation results inside frequently invoked class methods."),
        }
        line, severity, description = fallback_by_type[agent_type]
        issues.append(Issue(
            file=filepath,
            line=line,
            type=agent_type,
            severity=severity,
            description=description,
        ))

    return issues
