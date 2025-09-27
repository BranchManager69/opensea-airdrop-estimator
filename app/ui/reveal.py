"""Reveal presentation helpers for the estimate flow."""

from __future__ import annotations

import html
import time
from typing import Iterable, Tuple

import streamlit as st

Step = Tuple[str, str]


def run_reveal_presentation(steps: Iterable[Step], duration_seconds: int) -> None:
    """Animate the reveal timeline with a progress bar and step narration."""

    timeline = st.container()
    progress = timeline.progress(0, text="Preparing SEA airdrop projection…")
    narration = timeline.empty()

    steps_list = list(steps)
    total_steps = max(len(steps_list), 1)
    step_duration = max(duration_seconds / total_steps, 0.35)

    for idx, (title, detail) in enumerate(steps_list, start=1):
        progress.progress(
            int(idx / total_steps * 100),
            text=title,
        )
        safe_detail = html.escape(detail)
        safe_title = html.escape(title)
        narration.markdown(
            f"<div class='reveal-step'><span class='step-label'>{safe_title}</span>"
            f"<div class='step-detail'>{safe_detail}</div></div>",
            unsafe_allow_html=True,
        )
        time.sleep(step_duration)

    progress.empty()
    narration.empty()
    st.success("Projection ready — scroll to view your estimated allocation.")
