"""
Save Dialog Component - Modal dialog for saving runs to history.
"""

import time
import tempfile
import streamlit as st
from pathlib import Path
from services.history_service import HistoryService


@st.dialog("Save Run to History", width="medium")
def show_save_dialog(session_id, agent_prompt, fsm_instructions,
                     cost_metrics, parsed_clusters):
    """
    Display save dialog with notes input and run summary.

    Args:
        session_id: UUID session identifier
        agent_prompt: Voice agent system prompt (full text)
        fsm_instructions: FSM extraction instructions (full text)
        cost_metrics: Dictionary with 'total_cost_usd', token counts
        parsed_clusters: List of Cluster objects from ReportParser

    Actions:
        - On Save: Calls HistoryService.save_current_run() and shows success message
        - On Cancel: Closes dialog without saving
    """
    # Display run summary with standard metrics
    st.markdown("**Run Summary**")
    col1, col2, col3 = st.columns(3)

    with col1:
        cost = cost_metrics.get('total_cost_usd', 0.0)
        st.metric("Total Cost", f"${cost:.4f}")

    with col2:
        num_archetypes = len(parsed_clusters)
        st.metric("Archetypes", num_archetypes)

    with col3:
        num_paths = sum(
            1 + len(c.p1_paths) + len(c.p2_paths)
            for c in parsed_clusters
        )
        st.metric("Total Paths", num_paths)

    st.markdown("---")

    # Notes input
    notes = st.text_area(
        "Notes (optional)",
        height=100,
        placeholder="Add notes: test case, version, findings, etc.",
        key="save_dialog_notes"
    )

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Save", type="primary", use_container_width=True):
            history_service = HistoryService()
            try:
                # Get Supabase URLs and text content from save operation
                saved_data = history_service.save_current_run(
                    session_id,
                    agent_prompt,
                    fsm_instructions,
                    notes,
                    cost_metrics,
                    parsed_clusters
                )
                st.success(f"Run saved to history")

                # Create temp file for report text (mirrors load_run_data behavior)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                    tmp.write(saved_data['report_text'])
                    report_temp_path = tmp.name

                # Update session state with Supabase URLs and content
                st.session_state.flowchart_png_path = saved_data['flowchart_png_path']  # URL
                st.session_state.flowchart_dot_path = saved_data['flowchart_dot_path']  # Text
                st.session_state.report_path = report_temp_path                          # Temp file
                st.session_state.excel_report_path = saved_data.get('excel_report_path') # URL or None

                # Mark run as saved to prevent duplicate saves
                st.session_state.run_saved_to_history = True

                time.sleep(1)  # Brief pause to show success message
                st.session_state.show_save_dialog = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_save_dialog = False
            st.rerun()
