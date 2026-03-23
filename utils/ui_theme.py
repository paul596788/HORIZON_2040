from typing import Optional

import streamlit as st


def apply_horizon_theme(
    *,
    max_width: Optional[int] = 1280,
    top_padding: str = "1.6rem",
    bottom_padding: str = "3rem",
) -> None:
    width_rule = f"max-width: {max_width}px;" if max_width is not None else ""
    st.markdown(
        f"""
<style>
.stApp {{
background: radial-gradient(1200px 800px at 20% 0%, #111827 0%, #0b0f15 45%, #090c12 100%);
color: #e5e7eb;
}}
.block-container {{
padding-top: {top_padding};
padding-bottom: {bottom_padding};
width: 100%;
{width_rule}
}}
h1 {{
font-weight: 700;
letter-spacing: -0.02em;
}}
h2, h3 {{
color: #e2e8f0;
font-weight: 600;
}}
div[data-testid="stMetric"] {{
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 14px;
padding: 14px 16px;
}}
div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] label,
div[data-testid="stMetricLabel"] p {{
color: #cbd5e1 !important;
}}
div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] > div,
div[data-testid="stMetricValue"] p {{
color: #f8fafc !important;
font-weight: 700;
}}
div[data-testid="stMetricDelta"],
div[data-testid="stMetricDelta"] > div,
div[data-testid="stMetricDelta"] p,
div[data-testid="stMetricDelta"] svg {{
color: #86efac !important;
fill: #86efac !important;
}}
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {{
background: rgba(255,255,255,0.01);
border: 1px solid rgba(255,255,255,0.06);
border-radius: 16px;
}}
div[data-testid="stPlotlyChart"] {{
padding: 6px;
}}
</style>
""",
        unsafe_allow_html=True,
    )
