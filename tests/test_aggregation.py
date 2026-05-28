"""Issue post-processing: category filter and cross-agent dedupe."""
from models.schemas import Issue, IssueType, Severity
from reviewers._aggregation import deduplicate, filter_to_category


def _issue(file: str, desc: str, type_: IssueType, sev: Severity = Severity.MEDIUM, line: int = 1) -> Issue:
    return Issue(file=file, line=line, type=type_, severity=sev, description=desc)


def test_security_descriptions_kept_for_security_agent():
    issues = [
        _issue("a.py", "Hardcoded secret detected", IssueType.SECURITY),
        _issue("a.py", "Use of weak MD5 crypto algorithm", IssueType.SECURITY),
    ]
    kept = filter_to_category(issues, IssueType.SECURITY)
    assert len(kept) == 2


def test_security_descriptions_dropped_from_performance_agent():
    issues = [
        _issue("a.py", "Hardcoded secret detected", IssueType.PERFORMANCE),
        _issue("a.py", "Nested loop O(n^2) complexity", IssueType.PERFORMANCE),
    ]
    kept = filter_to_category(issues, IssueType.PERFORMANCE)
    assert len(kept) == 1
    assert "nested loop" in kept[0].description.lower()


def test_dedupe_collapses_same_file_same_description():
    issues = [
        _issue("a.py", "Hardcoded secret key in module", IssueType.SECURITY, Severity.HIGH),
        _issue("a.py", "Hardcoded secret key in module", IssueType.SECURITY, Severity.CRITICAL),
    ]
    deduped = deduplicate(issues)
    assert len(deduped) == 1
    assert deduped[0].severity == Severity.CRITICAL  # keeps highest severity


def test_dedupe_keeps_different_files_separate():
    issues = [
        _issue("a.py", "Hardcoded secret", IssueType.SECURITY),
        _issue("b.py", "Hardcoded secret", IssueType.SECURITY),
    ]
    assert len(deduplicate(issues)) == 2


def test_dedupe_keeps_different_descriptions():
    issues = [
        _issue("a.py", "Hardcoded secret in auth", IssueType.SECURITY),
        _issue("a.py", "Nested loop O(n^2) here", IssueType.PERFORMANCE),
    ]
    assert len(deduplicate(issues)) == 2
