"""1. PR Ingestion Node — loads changed files into state."""
import logging
import os
from typing import Any, Dict

from core.config import DEMO_DIR
from graph.state import GraphState

logger = logging.getLogger("Node.Ingestion")


_AUTH_DEMO = '''def verify_login(username, password):
    # SECURITY: Hardcoded secret keys
    SECRET_KEY = "SUPER_SECRET_12345"

    # BUG: Float conversion without exception handling
    ratio = float(username)

    if username == "admin" and password == SECRET_KEY:
        return True
    return False
'''

_UTILS_DEMO = '''import hashlib

def calculate_checksum(data):
    # SECURITY: Weak MD5 hash algorithm
    h = hashlib.md5()
    h.update(data.encode())
    return h.hexdigest()

def process_records(records):
    # PERFORMANCE: CPU intensive nested loop O(N^2)
    results = []
    for r1 in records:
        for r2 in records:
            if r1 != r2:
                results.append((r1, r2))
    return results

def read_log_file(filename):
    # PERFORMANCE: File opened without 'with' statement context manager
    f = open(filename, "r")
    content = f.read()
    return content
'''

_AUTH_PATCH = """@@ -1,7 +1,9 @@
 def verify_login(username, password):
+    # SECURITY: Hardcoded secret keys
     SECRET_KEY = "SUPER_SECRET_12345"
+
+    # BUG: Float conversion without exception handling
+    ratio = float(username)"""

_UTILS_PATCH = """@@ -1,15 +1,21 @@
 def calculate_checksum(data):
+    # SECURITY: Weak MD5 hash algorithm
     h = hashlib.md5()
     h.update(data.encode())
     return h.hexdigest()

 def process_records(records):
+    # PERFORMANCE: CPU intensive nested loop O(N^2)
     results = []"""


def _setup_demo_files() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    auth_path = DEMO_DIR / "auth.py"
    if not auth_path.exists():
        auth_path.write_text(_AUTH_DEMO)
    utils_path = DEMO_DIR / "utils.py"
    if not utils_path.exists():
        utils_path.write_text(_UTILS_DEMO)


def pr_ingestion_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Ingestion Node...")
    _setup_demo_files()

    changed_files = state.get("changed_files", []) or []

    if not changed_files:
        logger.info("No files passed. Loading mock workspace files for demonstration.")
        for filename, patch in (("auth.py", _AUTH_PATCH), ("utils.py", _UTILS_PATCH)):
            filepath = DEMO_DIR / filename
            content = filepath.read_text()
            changed_files.append({
                "path": os.path.join("fixtures", "demo_files", filename),
                "patch": patch,
                "content": content,
            })

    return {
        "changed_files": changed_files,
        "status": "ingested",
        "pr_id": state.get("pr_id", "demo-101"),
        "repo_name": state.get("repo_name", "sandbox/review-demo"),
        "commit_sha": state.get("commit_sha", "abc1234def"),
        "pr_title": state.get("pr_title", "Feature: Upgrade auth security and refactor utils loops"),
        "pr_body": state.get("pr_body", "Resolves login performance bottlenecks and secure connection issues."),
        "issues": [],
        "fixes": [],
        "evaluations": {},
        "human_decisions": {},
        "applied_fixes": [],
        "cost": state.get("cost", 0.0),
        "tokens_used": state.get("tokens_used", 0),
    }
