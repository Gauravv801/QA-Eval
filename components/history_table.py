"""
History Table Component - Interactive table view for run history.
"""

import time
import streamlit as st
from datetime import datetime, timezone, timedelta
from services.history_service import HistoryService


def format_datetime(iso_timestamp: str) -> str:
    """
    Format ISO timestamp to DD/MM/YY HH:MM in IST (UTC+5:30).

    Args:
        iso_timestamp: ISO 8601 format timestamp in UTC

    Returns:
        Formatted string in DD/MM/YY HH:MM format in IST
    """
    try:
        # Parse UTC timestamp
        dt_utc = datetime.fromisoformat(iso_timestamp)

        # Convert to IST (UTC+5:30)
        ist_offset = timedelta(hours=5, minutes=30)
        dt_ist = dt_utc + ist_offset

        return dt_ist.strftime("%d/%m/%y %H:%M")
    except (ValueError, AttributeError):
        # Fallback if parsing fails
        return iso_timestamp[:16]


def render_history_table():
    """
    Render interactive history table with basic Streamlit components.

    Displays all saved runs in descending chronological order (newest first).
    """
    history_service = HistoryService()
    runs = history_service.get_history_table_data()

    if not runs:
        st.info("No saved runs yet. Complete a pipeline run and click 'Save to History'.")
        return

    st.subheader(f"Run History ({len(runs)} runs)")

    # Render each run in a container
    for run in runs:
        with st.container():
            # Create grid layout
            col1, col2, col3, col4 = st.columns([15, 45, 25, 15])

            # Column 1: Date
            with col1:
                date_str = format_datetime(run["saved_at"])
                st.text(date_str)

            # Column 2: Prompt Preview + Notes
            with col2:
                # System prompt preview (primary)
                preview = run.get('agent_prompt_preview', '')
                st.text(preview[:100])  # Truncate to 100 chars

                # User notes (secondary, muted)
                notes = run.get('notes', '')
                if notes:
                    st.caption(f"Notes: {notes}")

            # Column 3: Metrics
            with col3:
                cost = run.get('total_cost_usd', 0.0)
                p0s = run.get('num_archetypes', 0)
                paths = run.get('num_total_paths', 0)

                st.text(f"Cost: ${cost:.4f}")
                st.text(f"P0: {p0s}")
                st.text(f"Paths: {paths}")

            # Column 4: Actions
            with col4:
                if st.button("View", key=f"view_{run['session_id']}", use_container_width=True):
                    st.session_state.view_mode = 'history_detail'
                    st.session_state.current_history_session_id = run['session_id']
                    st.rerun()

                if st.button("Delete", key=f"delete_{run['session_id']}", use_container_width=True):
                    st.session_state.delete_confirmation_session_id = run['session_id']
                    st.rerun()

            st.markdown("---")

    # Show delete confirmation dialog if triggered
    if st.session_state.delete_confirmation_session_id:
        show_delete_confirmation(st.session_state.delete_confirmation_session_id)


@st.dialog("Confirm Deletion", width="small")
def show_delete_confirmation(session_id):
    """
    Display delete confirmation dialog.

    Args:
        session_id: UUID session identifier for run to delete

    Actions:
        - On Delete: Calls HistoryService.delete_run_with_cleanup() and reloads table
        - On Cancel: Closes dialog without deleting
    """
    history_service = HistoryService()
    run = history_service.history_manager.get_run(session_id)

    if run:
        st.warning(f"Delete run from {format_datetime(run['saved_at'])}?")
        st.caption("This will permanently delete all outputs and cannot be undone.")
    else:
        st.error("Run not found.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                history_service.delete_run_with_cleanup(session_id)
                st.success("Deleted successfully")
                time.sleep(0.5)
                st.session_state.delete_confirmation_session_id = None
                st.rerun()
            except Exception as e:
                st.error(f"Deletion failed: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.delete_confirmation_session_id = None
            st.rerun()
