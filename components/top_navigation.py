"""
Top Navigation Component - Simple sidebar navigation.
"""

import streamlit as st
from utils.session_state import SessionStateManager


def render_top_navigation(page_title=None):
    """
    Render simple sidebar navigation.

    Args:
        page_title: Unused (kept for compatibility)

    View modes:
    - new_run: Shows "View Run History" button
    - history_table: Shows "New Run" button
    - history_detail: Shows "Back to History" button
    """
    st.sidebar.title("Navigation")

    current_mode = st.session_state.view_mode

    if current_mode == 'new_run':
        if st.sidebar.button("View Run History"):
            st.session_state.view_mode = 'history_table'
            st.rerun()

    elif current_mode == 'history_table':
        if st.sidebar.button("New Run"):
            SessionStateManager.reset()
            st.session_state.view_mode = 'new_run'
            st.rerun()

    elif current_mode == 'history_detail':
        if st.sidebar.button("Back to History"):
            st.session_state.view_mode = 'history_table'
            st.session_state.current_history_session_id = None
            st.rerun()
