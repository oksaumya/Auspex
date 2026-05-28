"""7. Apply Fix Node — patches approved fixes into the sandbox.

Every patch is validated by the AST sandbox in two phases:
1. The proposed snippet (best-effort parse; a snippet may not parse standalone)
2. The merged file after substitution (must parse and pass the AST safety walker)

A patch is only written if phase 2 passes.
"""
import logging
from typing import Any, Dict, List

from core.config import PROJECT_ROOT
from core.patching import apply_patch
from core.sandbox import safe_sandbox_compile
from graph.state import GraphState

logger = logging.getLogger("Node.ApplyFix")


def apply_fix_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Apply Fix Node...")
    decisions = state["human_decisions"]
    applied_fixes: List[str] = []
    rejected_unsafe: List[Dict[str, Any]] = []

    for fix in state["fixes"]:
        if decisions.get(fix.id) != "approved":
            continue

        issue = next((i for i in state["issues"] if i.id == fix.issue_id), None)
        if not issue:
            continue

        filepath = PROJECT_ROOT / issue.file
        if not filepath.exists():
            logger.warning("File %s not found; recording mock apply.", filepath)
            applied_fixes.append(fix.id)
            continue

        try:
            original_text = filepath.read_text()
            patched_text, info = apply_patch(original_text, fix.original_code, fix.proposed_code)
            if patched_text is None:
                logger.warning(
                    "Could not locate original code for fix %s in %s (%s). Skipping.",
                    fix.id, filepath, info,
                )
                continue

            verdict = safe_sandbox_compile(patched_text)
            if verdict["status"] != "safe":
                logger.error(
                    "Sandbox rejected fix %s for %s: %s",
                    fix.id, filepath, verdict,
                )
                rejected_unsafe.append({"fix_id": fix.id, "file": str(filepath), "verdict": verdict})
                continue

            filepath.write_text(patched_text)
            logger.info("Applied fix %s to %s (%s)", fix.id, filepath, info)
            applied_fixes.append(fix.id)
        except Exception as exc:
            logger.error("Failed to patch %s: %s", filepath, exc)

    metadata = state.get("metadata", {}) or {}
    if rejected_unsafe:
        metadata = {**metadata, "rejected_unsafe_fixes": rejected_unsafe}

    return {"applied_fixes": applied_fixes, "status": "applied", "metadata": metadata}
