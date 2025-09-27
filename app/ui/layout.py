"""Top-level layout helpers (header, global styles)."""

from __future__ import annotations

import streamlit as st

from app.config import LOGOMARK_PATH


def render_header() -> None:
    """Render the Sea Mom heading with supporting tagline."""

    header_container = st.container()
    with header_container:
        logo_col, text_col = st.columns([1, 6], gap="small")
        home_link = "https://sea.mom"
        with logo_col:
            if LOGOMARK_PATH.exists():
                logo_src = str(LOGOMARK_PATH)
                st.markdown(
                    f"<a href='{home_link}' class='header-home-link'><img src='{logo_src}' width='72' alt='Sea Mom logomark'></a>",
                    unsafe_allow_html=True,
                )
        with text_col:
            st.markdown(
                f"""
                <div style="text-align: left;">
                    <div style=\"display:flex; flex-wrap:wrap; align-items:center; gap:1rem; justify-content:space-between;\">
                        <a href='{home_link}' class='header-home-link title'>Sea Mom</a>
                        <span style="font-size: 1rem; color: #475569; white-space: nowrap;">
                            &ldquo;See, mom? I told you those 2021 NFT flips would pay off.&rdquo;
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def inject_global_styles() -> None:
    """Push shared CSS overrides used across Streamlit widgets."""

    st.markdown(
        """
        <style>
.header-home-link {
        text-decoration: none;
}
.header-home-link.title {
        font-size: 2.4rem;
        font-weight: 700;
        color: #04111d;
}
.header-home-link.title:hover {
        color: #1868B7;
}
    
/* Primary CTA */
div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #2081E2, #1868B7);
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 600;
        padding: 0.95rem 3rem;
        border-radius: 18px;
        border: none;
        box-shadow: 0 15px 32px rgba(32, 129, 226, 0.32);
        white-space: nowrap;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        max-width: 420px;
        margin: 0 auto;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover:not(:disabled) {
        box-shadow: 0 20px 36px rgba(32, 129, 226, 0.38);
        transform: translateY(-1px);
    }
    div[data-testid="stButton"] button[kind="primary"]:disabled {
        background: #94a3b8;
        box-shadow: none;
        cursor: not-allowed;
    }
    .wallet-lookup div[data-testid="stButton"] button {
        background: linear-gradient(135deg, rgba(32,129,226,0.95), rgba(12,52,93,0.92));
        color: #f8fafc;
        font-size: 0.95rem;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        max-width: none;
        margin: 0;
    }
    .wallet-lookup div[data-testid="stButton"] button:hover:not(:disabled) {
        box-shadow: 0 10px 22px rgba(12, 52, 93, 0.35);
        transform: translateY(-1px);
    }
    .wallet-lookup .wallet-input > div[data-baseweb="input"] {
        border-radius: 12px;
        border: 1px solid rgba(32, 129, 226, 0.18);
        box-shadow: 0 6px 16px rgba(4, 17, 29, 0.08);
    }
    .wallet-lookup .wallet-input input {
        font-size: 1rem;
    }
    .wallet-lookup {
        background: rgba(240, 247, 255, 0.72);
        border: 1px solid rgba(32, 129, 226, 0.2);
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.8rem;
    }
    .insight-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: center;
        margin-top: 1.75rem;
    }
    .insight-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px;
        padding: 1rem 1.35rem;
        min-width: 180px;
        max-width: 240px;
        color: #e2e8f0;
    }
    .insight-card h4 {
        margin: 0 0 0.35rem 0;
        font-size: 0.85rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .insight-card .value {
        font-size: 1.55rem;
        font-weight: 600;
        margin: 0;
    }
    .insight-card .hint {
        margin-top: 0.2rem;
        font-size: 0.85rem;
        color: #cbd5f5;
        opacity: 0.85;
    }
    .stepper {
        margin-top: 2rem;
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 1.6rem 1.8rem;
        color: #e2e8f0;
    }
    .stepper h4 {
        margin: 0 0 1rem 0;
        text-align: center;
        font-size: 0.95rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .stepper-list {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin: 0;
        padding: 0;
        list-style: none;
    }
    .stepper-item {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }
    .stepper-index {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #2081E2, #1868B7);
        color: #e2e8f0;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .stepper-content {
        flex: 1;
    }
    .stepper-content .title {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.15rem;
    }
    .stepper-content .detail {
        font-size: 0.95rem;
        color: #cbd5f5;
    }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stSlider"] label {
        color: #2081E2 !important;
        font-weight: 600 !important;
    }
    .cohort-timeline {
        margin: 1.2rem auto 0.8rem auto;
        max-width: 800px;
    }
    .cohort-cards-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.2rem;
    }
    .cohort-card-link {
        text-decoration: none;
    }
    .cohort-card {
        border-radius: 16px;
        border: 1px solid rgba(226, 230, 239, 0.85);
        background: rgba(255, 255, 255, 0.96);
        padding: 1.2rem 1.4rem;
        box-shadow: 0 10px 20px rgba(4, 17, 29, 0.08);
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    }
    .cohort-card-link:hover .cohort-card {
        transform: translateY(-6px);
        box-shadow: 0 18px 32px rgba(4, 17, 29, 0.16);
        border-color: rgba(32, 129, 226, 0.35);
    }
    .cohort-card.selected {
        background: linear-gradient(135deg, rgba(32, 129, 226, 0.95), rgba(12, 52, 93, 0.92));
        border-color: rgba(32, 129, 226, 0.7);
        box-shadow: 0 22px 40px rgba(32, 129, 226, 0.35);
    }
    .cohort-card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #04111d;
        letter-spacing: 0.02em;
    }
    .cohort-card.selected .cohort-card-title {
        color: #f8fafc;
    }
    .cohort-card-year {
        font-size: 0.95rem;
        color: #1868B7;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .cohort-card.selected .cohort-card-year {
        color: #d4e7f9;
    }
    .cohort-card-metric {
        font-size: 0.95rem;
        color: #353840;
    }
    .cohort-card.selected .cohort-card-metric {
        color: #f8fafc;
    }
    .cohort-description {
        font-size: 0.95rem;
        color: #353840;
        background: rgba(226, 230, 239, 0.45);
        border: 1px solid rgba(226, 230, 239, 0.9);
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin-top: 0.6rem;
    }
    .scenario-cards .cohort-card {
        background: rgba(245, 248, 255, 0.96);
        border-color: rgba(32, 129, 226, 0.12);
        box-shadow: 0 12px 28px rgba(4, 17, 29, 0.12);
    }
    .scenario-card-metric {
        font-size: 1.5rem;
        font-weight: 700;
        color: #04111d;
    }
    .scenario-card-submetric {
        font-size: 1rem;
        color: #1868B7;
        font-weight: 600;
    }
    .scenario-card-foot {
        font-size: 0.95rem;
        color: #353840;
    }
    .scenario-card-foot.subtle {
        color: #6b7280;
        font-size: 0.85rem;
    }
    .scenario-card.selected {
        background: linear-gradient(135deg, rgba(32, 129, 226, 0.95), rgba(12, 52, 93, 0.92));
        color: #f8fafc;
    }
    .scenario-card.selected .scenario-card-submetric,
    .scenario-card.selected .scenario-card-foot,
    .scenario-card.selected .scenario-card-metric,
    .scenario-card.selected .cohort-card-year,
    .scenario-card.selected .cohort-card-title {
        color: #f8fafc;
    }
    .scenario-strip {
        margin: 2rem 0 1.25rem 0;
        text-align: center;
    }
    .scenario-strip-header {
        font-size: 1.35rem;
        font-weight: 700;
        color: #04111d;
    }
    .scenario-strip-lead {
        margin: 0.35rem auto 0;
        max-width: 660px;
        color: #475569;
        font-size: 1rem;
    }
    .scenario-card-sparkline {
        margin-top: 1rem;
    }
    .scenario-card.selected .scenario-card-sparkline-svg path[stroke] {
        stroke: rgba(248, 250, 252, 0.92);
    }
    .scenario-card.selected .scenario-card-sparkline-svg circle {
        stroke: rgba(4, 17, 29, 0.45);
    }
    .scenario-card-sparkline-svg {
        width: 100%;
        height: 64px;
    }
    .scenario-slider-label {
        margin-top: 1.5rem;
        font-weight: 600;
        font-size: 0.95rem;
        color: #1868B7;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .results-banner {
        margin: 1rem 0 1.5rem 0;
        padding: 1.4rem 1.8rem;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(32, 129, 226, 0.12), rgba(12, 52, 93, 0.08));
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        align-items: center;
        justify-content: space-between;
    }
    .results-banner-metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
    }
    .metric-block {
        min-width: 180px;
    }
    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #0c345d;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #04111d;
    }
    .metric-hint {
        font-size: 0.95rem;
        color: #475569;
        margin-top: 0.2rem;
    }
    .results-banner-share {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        min-width: 220px;
    }
    .results-banner-share img {
        max-width: 240px;
        border-radius: 12px;
        box-shadow: 0 14px 28px rgba(4, 17, 29, 0.18);
    }
    .share-placeholder {
        width: 220px;
        text-align: center;
        font-size: 0.9rem;
        padding: 1.4rem;
        border-radius: 12px;
        border: 1px dashed rgba(32, 129, 226, 0.35);
        color: #1868B7;
        background: rgba(255, 255, 255, 0.75);
    }
    .share-link {
        font-weight: 600;
        color: #1868B7;
        text-decoration: none;
    }
    .share-link:hover {
        text-decoration: underline;
    }
    .tweet-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.6rem 1.4rem;
        border-radius: 999px;
        background: #1d9bf0;
        color: #f8fafc;
        font-weight: 600;
        text-decoration: none;
        margin-top: 0.4rem;
        box-shadow: 0 8px 20px rgba(29, 155, 240, 0.25);
    }
    .tweet-button:hover {
        text-decoration: none;
        box-shadow: 0 12px 24px rgba(29, 155, 240, 0.32);
    }
    .fee-highlight {
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
        padding: 1.1rem 1.4rem;
        border-radius: 14px;
        background: rgba(226, 238, 255, 0.55);
        border: 1px solid rgba(32, 129, 226, 0.18);
    }
    .fee-highlight-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #0c345d;
        margin-bottom: 0.6rem;
    }
    .fee-highlight-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
    }
    .fee-highlight-item .label {
        display: block;
        font-size: 0.85rem;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.15rem;
    }
    .fee-highlight-item .value {
        display: block;
        font-size: 1.45rem;
        font-weight: 700;
        color: #04111d;
    }
    .fee-highlight-item .hint {
        display: block;
        font-size: 0.9rem;
        color: #2563eb;
        margin-top: 0.1rem;
    }
        </style>
        """,
        unsafe_allow_html=True,
    )
