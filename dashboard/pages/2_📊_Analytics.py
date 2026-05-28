"""System-wide analytics — data is sourced from /api/analytics/summary."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _api_client import analytics_summary  # noqa: E402
from _styles import inject_styles  # noqa: E402

st.set_page_config(page_title="System Analytics", page_icon="📊", layout="wide")
inject_styles()

st.title("📊 Code Review Analytics Dashboard")
st.markdown(
    "<p style='color:#94a3b8;'>Live metrics aggregated across every active PR review session.</p>",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=5)
def _cached_summary():
    return analytics_summary()


summary = _cached_summary()
if not summary:
    st.error("Could not reach the backend analytics endpoint.")
    st.info("Start the backend with: `uvicorn server:app --reload`")
    st.stop()


def metric_card(value, label, color) -> str:
    return (
        f"<div class='glass-card' style='text-align:center;'>"
        f"<h3 style='margin:0; color:{color}; font-size:2.8rem;'>{value}</h3>"
        f"<p style='margin: 4px 0 0 0; color:#cbd5e1; font-weight:600;'>{label}</p>"
        f"</div>"
    )


col1, col2, col3, col4 = st.columns(4)
col1.markdown(metric_card(summary["total_prs"], "Total PRs reviewed", "#818cf8"), unsafe_allow_html=True)
col2.markdown(metric_card(summary["total_issues"], "Issues raised", "#34d399"), unsafe_allow_html=True)
col3.markdown(
    metric_card(f"{summary['acceptance_rate']}%", "Fixes accepted rate", "#fb7185"),
    unsafe_allow_html=True,
)
col4.markdown(
    metric_card(f"{summary['avg_confidence']}%", "Avg confidence score", "#fbbf24"),
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("📈 Self-evaluation confidence by PR")
    trend = summary.get("confidence_trend", [])
    if trend:
        df = pd.DataFrame(
            [t["confidence"] for t in trend],
            index=[t["pr_id"] for t in trend],
            columns=["Confidence (%)"],
        )
        st.line_chart(df)
    else:
        st.info("No completed self-evaluations yet — confidence trend will appear after the first PR finishes review.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("💳 Cost and tokens")
    cost = summary.get("cost_breakdown_usd", 0.0)
    tokens = summary.get("tokens_used", 0)
    cost_cols = st.columns(2)
    cost_cols[0].metric("Cumulative cost (USD)", f"${cost:.4f}")
    cost_cols[1].metric("Tokens consumed", f"{tokens:,}")
    st.caption("Cost is estimated from Groq's published per-1M token pricing.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🍩 Defect classification")
    dist = summary.get("defect_distribution", {})
    total = sum(dist.values()) or 1
    ratio_cols = st.columns(3)
    ratio_cols[0].metric("🐞 Bugs", f"{round(dist.get('BUG', 0) / total * 100)}%")
    ratio_cols[1].metric("🛡️ Security", f"{round(dist.get('SECURITY', 0) / total * 100)}%")
    ratio_cols[2].metric("⚡ Performance", f"{round(dist.get('PERFORMANCE', 0) / total * 100)}%")
    st.markdown("<br>", unsafe_allow_html=True)
    if any(dist.values()):
        chart_df = pd.DataFrame(
            [dist.get("BUG", 0), dist.get("SECURITY", 0), dist.get("PERFORMANCE", 0)],
            index=["Bugs", "Security", "Performance"],
            columns=["Issue count"],
        )
        st.bar_chart(chart_df)
    else:
        st.info("No issues yet — defect distribution updates after the first review.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🎓 Learning telemetry")
    total_rejected = summary.get("total_rejections_logged", 0)
    st.markdown(f"**Total registered human rejections:** `{total_rejected}`")
    recent = summary.get("recent_rejections", [])
    if recent:
        st.markdown("**Recent rejection insights:**")
        for idx, item in enumerate(recent):
            reason = item.get("reason", "(no reason captured)")
            ts = item.get("timestamp", "")
            st.markdown(f"- *#{idx + 1} ({ts}):* `{reason}`")
    else:
        st.info("No rejections registered yet. The system is fully aligned with developer approvals.")
    st.markdown("</div>", unsafe_allow_html=True)
