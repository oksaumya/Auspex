"""PyGithub helpers for fetching changed file content from a real PR."""
import base64
import logging
from typing import Any, Dict, List, Optional

from core.config import GITHUB_TOKEN

logger = logging.getLogger("GitHubFetch")


def fetch_pr_files(repo_name: str, pr_number: int) -> Optional[List[Dict[str, Any]]]:
    """Fetches changed files for a PR. Returns None if PyGithub is unavailable
    or ``GITHUB_TOKEN`` is unset. Otherwise returns a list of
    ``{"path", "patch", "content"}`` dicts ready for the graph state.

    Binary files and files larger than ~1MB are skipped.
    """
    if not GITHUB_TOKEN:
        logger.info("GITHUB_TOKEN not set; cannot fetch live PR files.")
        return None

    try:
        from github import Auth, Github
    except ImportError:
        logger.warning("PyGithub not installed; cannot fetch live PR files.")
        return None

    try:
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = gh.get_repo(repo_name)
        pull = repo.get_pull(pr_number)
        head_sha = pull.head.sha
    except Exception as exc:
        logger.error("Failed to load PR %s#%s: %s", repo_name, pr_number, exc)
        return None

    out: List[Dict[str, Any]] = []
    for file_obj in pull.get_files():
        if file_obj.status in ("removed",):
            continue
        try:
            content_obj = repo.get_contents(file_obj.filename, ref=head_sha)
        except Exception as exc:
            logger.warning("Skipping %s: %s", file_obj.filename, exc)
            continue

        if getattr(content_obj, "encoding", None) != "base64":
            continue
        try:
            content_bytes = base64.b64decode(content_obj.content)
            content_text = content_bytes.decode("utf-8")
        except Exception:
            logger.info("Skipping binary file %s", file_obj.filename)
            continue

        out.append({
            "path": file_obj.filename,
            "patch": file_obj.patch or "",
            "content": content_text,
        })

    logger.info("Fetched %d files for %s#%s via PyGithub.", len(out), repo_name, pr_number)
    return out
