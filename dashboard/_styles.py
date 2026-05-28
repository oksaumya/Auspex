"""Shared glassmorphic CSS for every Streamlit page."""
import streamlit as st

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    .stMarkdown pre code, code {
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25);
        transition: transform 0.25s ease, border-color 0.25s ease;
    }
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }
    .glowing-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(129, 140, 248, 0.15);
        margin-bottom: 10px;
    }
    .issue-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        transition: all 0.25s ease;
    }
    .issue-card-approved {
        border: 1px solid rgba(52, 211, 153, 0.4);
        box-shadow: 0 0 15px rgba(52, 211, 153, 0.08);
    }
    .issue-card-rejected {
        border: 1px solid rgba(239, 68, 68, 0.3);
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.05);
        opacity: 0.8;
    }
    .issue-card-pending {
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
    }
    .badge-BUG {
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgb(59, 130, 246);
        color: #bfdbfe;
    }
    .badge-SECURITY {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgb(239, 68, 68);
        color: #fca5a5;
    }
    .badge-PERFORMANCE {
        background: rgba(234, 179, 8, 0.15);
        border: 1px solid rgb(234, 179, 8);
        color: #fef08a;
    }
    .severity-CRITICAL {
        background: rgba(239, 68, 68, 0.25);
        color: #fca5a5;
        border: 1px solid rgb(239, 68, 68);
    }
    .severity-HIGH {
        background: rgba(249, 115, 22, 0.2);
        color: #fed7aa;
        border: 1px solid rgb(249, 115, 22);
    }
    .severity-MEDIUM {
        background: rgba(234, 179, 8, 0.2);
        color: #fef08a;
        border: 1px solid rgb(234, 179, 8);
    }
    .severity-LOW {
        background: rgba(16, 185, 129, 0.2);
        color: #a7f3d0;
        border: 1px solid rgb(16, 185, 129);
    }
    .diff-box {
        padding: 12px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        background: #0b0f19;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .diff-box h5 {
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #94a3b8;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 4px;
    }
</style>
"""


def inject_styles() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
