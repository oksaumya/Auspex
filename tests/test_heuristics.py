"""Heuristic reviewer produces type-correct findings when no LLM is available."""
from models.schemas import IssueType
from reviewers.heuristics import run_mock_review


_AUTH = '''def verify_login(username, password):
    SECRET_KEY = "SUPER_SECRET_12345"
    ratio = float(username)
    return True
'''


_UTILS = '''import hashlib

def calculate_checksum(data):
    h = hashlib.md5()
    return h.hexdigest()

def process_records(records):
    results = []
    for r1 in records:
        for r2 in records:
            results.append((r1, r2))
    return results
'''


def test_bug_agent_returns_bug_typed_issues():
    issues = run_mock_review("a.py", _AUTH, "", IssueType.BUG)
    assert issues
    assert all(i.type == IssueType.BUG for i in issues)


def test_security_agent_finds_hardcoded_secret():
    issues = run_mock_review("a.py", _AUTH, "", IssueType.SECURITY)
    assert any("hardcoded" in i.description.lower() or "secret" in i.description.lower() for i in issues)
    assert all(i.type == IssueType.SECURITY for i in issues)


def test_security_agent_flags_md5():
    issues = run_mock_review("u.py", _UTILS, "", IssueType.SECURITY)
    assert any("md5" in i.description.lower() or "weak" in i.description.lower() for i in issues)


def test_performance_agent_flags_nested_loop():
    issues = run_mock_review("u.py", _UTILS, "", IssueType.PERFORMANCE)
    assert any("nested loop" in i.description.lower() or "n^2" in i.description.lower() for i in issues)
    assert all(i.type == IssueType.PERFORMANCE for i in issues)


def test_empty_content_returns_fallback():
    for kind in (IssueType.BUG, IssueType.SECURITY, IssueType.PERFORMANCE):
        issues = run_mock_review("e.py", "", "", kind)
        assert len(issues) == 1
        assert issues[0].type == kind
