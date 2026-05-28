"""Streamlit landing page. Run with: `streamlit run dashboard/Home.py`."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _api_client import server_health  # noqa: E402
from _styles import inject_styles  # noqa: E402

st.set_page_config(
    page_title="Auspex",
    page_icon="🜨",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()

st.markdown("<h1 class='glowing-title'>Auspex</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:1.2rem; color:#94a3b8;'>Reads the omens in every commit — multi-agent PR review on LangGraph &amp; Groq.</p>",
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(
        """
        <div class='glass-card'>
            <h3>System workspace active</h3>
            <p>Welcome to the human-in-the-loop AI review environment. This system scans pull request changes, performs codebase search via hybrid vector + keyword retrieval, and triggers parallel sub-agents (Bug, Security, Performance) to audit your commits.</p>
            <p>Select a workspace module from the sidebar to begin:</p>
            <ul>
                <li><strong>🛡️ Live PR Review</strong>: Inspect real-time code issues, view proposed edits via diff views, review critiques, and approve/reject individual fixes.</li>
                <li><strong>📊 System Analytics</strong>: Track historical review conversion rates, cost projections, issue classifications, and agent confidence telemetry.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='glass-card'>
            <h3>Agent architecture nodes</h3>
            <p>The code reviewer graph consists of the following compiled nodes:</p>
            <ol>
                <li><strong>PR Ingestion</strong>: Hook parser receiving pull request file modifications.</li>
                <li><strong>Context Retrieval</strong>: Codebase hybrid search (Qdrant dense + BM25 sparse) + Cohere reranking.</li>
                <li><strong>Parallel Sub-agents</strong>: Concurrent analysis per file via <em>Bug Hunter</em>, <em>Security Scanner</em>, and <em>Performance Reviewer</em>.</li>
                <li><strong>Fix Generation</strong>: Typed Pydantic fix proposal engine.</li>
                <li><strong>Self-Evaluation</strong>: Multidimensional critique scoring confidence 0-100.</li>
                <li><strong>Human-in-the-Loop</strong>: Thread interrupt state boundary awaiting review.</li>
                <li><strong>Apply Fix</strong>: Sandbox workspace patch editor.</li>
                <li><strong>Learning</strong>: Local rejection database for future model alignment.</li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Backend server status")
    health = server_health()
    if health:
        st.success("API Server Online")
        st.json(
            {
                "Service": health.get("service"),
                "Docs": "http://127.0.0.1:8000/docs",
                "Local Time": health.get("local_time"),
                "Version": "v2.0.0",
            }
        )
    else:
        st.error("API Server Offline")
        st.info("Start the backend with: `uvicorn server:app --reload`")
    st.markdown("</div>", unsafe_allow_html=True)

    import os

    keys = [
        ("Groq API", bool(os.getenv("GROQ_API_KEY")), "#818cf8"),
        ("Cohere Rerank", bool(os.getenv("COHERE_API_KEY")), "#a78bfa"),
        ("LangSmith", os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true", "#f472b6"),
        ("GitHub Webhook Secret", bool(os.getenv("GITHUB_WEBHOOK_SECRET")), "#34d399"),
    ]
    rows = "".join(
        f"<tr><td style='padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);'>{label}</td>"
        f"<td style='text-align: right; color:{color};'>{'Configured 🟢' if present else 'Not set ⚪'}</td></tr>"
        for label, present, color in keys
    )
    st.markdown(
        f"""
        <div class='glass-card'>
            <h3>Loaded API keys</h3>
            <table style='width:100%; border-collapse: collapse;'>
                {rows}
            </table>
            <p style='margin-top: 12px; font-size: 0.85rem; color:#94a3b8;'>Missing keys fall back to deterministic heuristics — the system still produces fixes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
