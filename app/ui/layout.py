"""Top-level layout helpers (header, global styles)."""

from __future__ import annotations

import streamlit as st

from app.config import LOGOMARK_PATH


def render_header() -> None:
    """Render the Sea Mom heading with supporting tagline."""

    header_container = st.container()
    with header_container:
        logo_col, text_col = st.columns([1, 6], gap="small")
        with logo_col:
            if LOGOMARK_PATH.exists():
                st.image(str(LOGOMARK_PATH), width=72)
        with text_col:
            st.markdown(
                """
                <div style="text-align: left;">
                    <div style="display:flex; flex-wrap:wrap; align-items:center; gap:1rem; justify-content:space-between;">
                        <h1 style="margin: 0; color: #04111d;">Sea Mom</h1>
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
        </style>
        """,
        unsafe_allow_html=True,
    )
