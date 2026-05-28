"""Live PR review interface with per-sub-agent tabs."""
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _api_client import (  # noqa: E402
    get_session,
    list_sessions,
    resume_session,
    submit_decision,
)
from _styles import inject_styles  # noqa: E402

st.set_page_config(page_title="Live PR Review", page_icon="🛡️", layout="wide")
inject_styles()

st.title("🛡️ Live PR Review Dashboard")
st.markdown(
    "<p style='color:#94a3b8;'>Inspect code issues, critique proposed fixes, and run automated sandbox merges.</p>",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=2)
def _cached_sessions():
    return list_sessions()


@st.cache_data(ttl=2)
def _cached_session(pr_id: str):
    return get_session(pr_id)


sessions = _cached_sessions()

with st.sidebar:
    st.markdown("### 🔍 Select active PR")
    selected_pr_id = st.selectbox("Pull Request ID", sessions)
    st.markdown("---")
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

session_data = _cached_session(selected_pr_id)

if not session_data:
    st.error("Could not fetch PR session. Make sure the FastAPI service is running.")
    st.info("Start the backend with: `uvicorn server:app --reload`")
    st.stop()

status = session_data.get("status", "pending")
status_color = (
    "#38bdf8" if status == "waiting_for_approval" else ("#34d399" if status == "completed" else "#94a3b8")
)
commit_sha = (session_data.get("commit_sha") or "unknown")[:7]

st.markdown(
    f"""
    <div class='glass-card'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <h3 style='margin:0;'>{session_data.get("pr_title")}</h3>
                <p style='color:#94a3b8; margin: 4px 0 0 0;'>Repo: {session_data.get("repo_name")} | PR #{session_data.get("pr_id")} | Commit: <code style='color:#a78bfa;'>{commit_sha}</code></p>
            </div>
            <div style='text-align:right;'>
                <span class='badge' style='background: rgba(255,255,255,0.05); border: 1px solid {status_color}; color: {status_color}; font-size:1rem; padding: 6px 16px;'>{status.upper().replace("_", " ")}</span>
            </div>
        </div>
        <p style='margin: 12px 0 0 0; color:#cbd5e1; font-size:0.95rem;'>{session_data.get("pr_body")}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

issues = session_data.get("issues", [])
fixes = session_data.get("fixes", [])
evaluations = session_data.get("evaluations", {})
decisions = session_data.get("human_decisions", {})
applied = session_data.get("applied_fixes", [])

if not issues:
    st.success("🎉 No issues identified! All sub-agents gave the code a green light.")
else:
    fixes_lookup = {(f.get("issue_id") if isinstance(f, dict) else f.issue_id): f for f in fixes}

    def _attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    grouped: dict[str, list] = {"BUG": [], "SECURITY": [], "PERFORMANCE": []}
    for issue in issues:
        kind = str(_attr(issue, "type", "BUG"))
        grouped.setdefault(kind, []).append(issue)

    tab_labels = [
        f"🐞 Bug Hunter ({len(grouped['BUG'])})",
        f"🛡️ Security Scanner ({len(grouped['SECURITY'])})",
        f"⚡ Performance ({len(grouped['PERFORMANCE'])})",
    ]
    tab_bug, tab_sec, tab_perf = st.tabs(tab_labels)

    def render_issue(issue) -> None:
        issue_id = _attr(issue, "id")
        issue_type = _attr(issue, "type", "BUG")
        severity = _attr(issue, "severity", "MEDIUM")
        file_path = _attr(issue, "file", "unknown.py")
        line_no = _attr(issue, "line", 1)
        description = _attr(issue, "description", "")

        fix = fixes_lookup.get(issue_id)
        fix_id = _attr(fix, "id", "") if fix else ""
        decision = decisions.get(fix_id, "pending")

        card_class = (
            "issue-card-approved" if decision == "approved"
            else ("issue-card-rejected" if decision == "rejected" else "issue-card-pending")
        )

        st.markdown(
            f"""
            <div class='issue-card {card_class}'>
                <span class='badge badge-{issue_type}'>{issue_type}</span>
                <span class='badge severity-{severity}'>{severity}</span>
                <span style='color:#94a3b8; font-size:0.9rem;'>File: <code>{file_path}</code> | Line: {line_no}</span>
                <h4 style='margin: 8px 0 0 0;'>{description}</h4>
            """,
            unsafe_allow_html=True,
        )

        if fix:
            explanation = _attr(fix, "explanation", "")
            original_code = _attr(fix, "original_code", "")
            proposed_code = _attr(fix, "proposed_code", "")

            st.markdown(
                "<h5 style='margin-bottom:6px; color:#c084fc;'>💡 Proposed correction</h5>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='color:#cbd5e1; font-size:0.95rem; margin-top:0;'>{explanation}</p>",
                unsafe_allow_html=True,
            )

            col_orig, col_prop = st.columns(2)
            with col_orig:
                st.markdown("<div class='diff-box'><h5>Original code</h5></div>", unsafe_allow_html=True)
                st.code(original_code, language="python")
            with col_prop:
                st.markdown("<div class='diff-box'><h5>Proposed fix</h5></div>", unsafe_allow_html=True)
                st.code(proposed_code, language="python")

            eval_obj = evaluations.get(fix_id)
            if eval_obj:
                conf = _attr(eval_obj, "confidence", 90)
                correctness = _attr(eval_obj, "correctness_score", 90)
                security_score = _attr(eval_obj, "security_score", 90)
                compatibility = _attr(eval_obj, "compatibility_score", 90)
                risk_lvl = _attr(eval_obj, "risk_level", "LOW")
                reasoning = _attr(eval_obj, "reasoning", "")

                bar_color = "green" if conf >= 85 else ("orange" if conf >= 65 else "red")
                st.markdown(
                    f"""
                    <div style='margin-top: 12px; display:flex; align-items:center; justify-content:space-between;'>
                        <div style='width: 70%;'>
                            <span style='font-size:0.9rem; color:#94a3b8;'>Agent confidence score</span>
                            <div style='background:rgba(255,255,255,0.05); height:8px; border-radius:4px; margin-top:4px;'>
                                <div style='background:{bar_color}; width:{conf}%; height:8px; border-radius:4px;'></div>
                            </div>
                        </div>
                        <div style='font-size:1.4rem; font-weight:800; color:#f8fafc;'>{conf}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.expander("📝 View multi-agent self-critique scores"):
                    crit_cols = st.columns(4)
                    crit_cols[0].metric("Correctness", f"{correctness}%")
                    crit_cols[1].metric("Security", f"{security_score}%")
                    crit_cols[2].metric("Compatibility", f"{compatibility}%")
                    crit_cols[3].metric("Risk impact", str(risk_lvl))
                    st.markdown(f"**Critique logic:** *{reasoning}*")

            st.markdown("<br>", unsafe_allow_html=True)
            btn_cols = st.columns([1, 1, 4])
            if btn_cols[0].button("✅ Approve", key=f"app_{fix_id}"):
                if submit_decision(selected_pr_id, fix_id, "approved"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to submit approval.")
            if btn_cols[1].button("❌ Reject", key=f"rej_{fix_id}"):
                if submit_decision(selected_pr_id, fix_id, "rejected"):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to submit rejection.")

        st.markdown("</div>", unsafe_allow_html=True)

    for tab, kind in ((tab_bug, "BUG"), (tab_sec, "SECURITY"), (tab_perf, "PERFORMANCE")):
        with tab:
            kind_issues = grouped.get(kind, [])
            if not kind_issues:
                st.info(f"No {kind.lower()} issues raised for this PR.")
                continue
            st.caption(
                {
                    "BUG": "Algorithmic correctness, null safety, and boundary conditions.",
                    "SECURITY": "OWASP Top 10, hardcoded secrets, injection risk, weak crypto.",
                    "PERFORMANCE": "Resource leaks, nested loops, query bottlenecks.",
                }[kind]
            )
            for issue in kind_issues:
                render_issue(issue)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🏁 Finish review session")

    pending_fixes = [fid for fid, dec in decisions.items() if dec == "pending"]
    if pending_fixes:
        st.info(f"Submitting reviews requires a choice on all proposed refactors. Remaining: {len(pending_fixes)}")
        st.button("🚀 Apply approved fixes", disabled=True)
    else:
        st.success("All changes have been approved or rejected.")
        if status in ("applied", "completed"):
            st.info("Pipeline already ran — changes committed to the sandbox.")
            if applied:
                st.markdown("**Applied fixes:**")
                for app_id in applied:
                    st.markdown(f"- Code Fix `{app_id}` written to local file editor sandbox.")
        else:
            if st.button("🚀 Apply approved fixes", key="resume_graph_btn"):
                with st.spinner("Resuming LangGraph state machine..."):
                    if resume_session(selected_pr_id):
                        st.success("Pipeline resumed. Applying patches to local file sandbox.")
                        time.sleep(1.5)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Failed to resume session. Check the backend logs.")
    st.markdown("</div>", unsafe_allow_html=True)
