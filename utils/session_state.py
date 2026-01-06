import streamlit as st
import uuid
import shutil
from pathlib import Path

class SessionStateManager:
    """
    Centralized session state management for the Streamlit QA Evaluation Pipeline.

    Manages all session state variables in one place to ensure consistency
    and provide easy initialization and reset functionality.
    """

    @staticmethod
    def initialize():
        """
        Initialize all session state variables if not already set.

        This method is idempotent - it can be safely called multiple times
        without overwriting existing state.

        Session Variables:
            - session_id (str): Unique UUID for session isolation
            - pipeline_running (bool): Flag to disable UI during execution
            - current_step (int): Pipeline progress (0=idle, 1=gen, 2=viz, 3=analysis)
            - thinking_text (str): Accumulated Claude thinking output
            - output_text (str): Accumulated Claude response text
            - output_json (dict): Parsed FSM JSON from script_1
            - cost_metrics (dict): API cost data from script_1
            - flowchart_png_path (str): Absolute path to generated PNG
            - flowchart_dot_path (str): Absolute path to DOT source
            - report_path (str): Absolute path to analysis report
            - parsed_clusters (list): Structured cluster data from report_parser
            - excel_report_path (str): Absolute path to Excel export file
            - excel_error (str | None): Excel generation error message if failed
            - active_tab (str): Currently active tab in tabbed interface
            - view_mode (str): Current view mode ('new_run' | 'history_table' | 'history_detail')
            - current_history_session_id (str | None): Session ID when viewing historical run
            - show_save_dialog (bool): Flag to trigger save run dialog
            - history_agent_prompt (str): Agent prompt from historical run
            - history_fsm_instructions (str): FSM instructions from historical run
            - history_run_metadata (dict | None): Full metadata for current historical run
            - delete_confirmation_session_id (str | None): Session ID awaiting delete confirmation
            - run_saved_to_history (bool): Flag indicating current run has been saved
        """
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

        if 'pipeline_running' not in st.session_state:
            st.session_state.pipeline_running = False

        if 'current_step' not in st.session_state:
            st.session_state.current_step = 0  # 0: idle, 1: gen, 2: viz, 3: analysis

        if 'thinking_text' not in st.session_state:
            st.session_state.thinking_text = ""

        if 'output_text' not in st.session_state:
            st.session_state.output_text = ""

        if 'output_json' not in st.session_state:
            st.session_state.output_json = None

        if 'cost_metrics' not in st.session_state:
            st.session_state.cost_metrics = None

        if 'flowchart_png_path' not in st.session_state:
            st.session_state.flowchart_png_path = None

        if 'flowchart_dot_path' not in st.session_state:
            st.session_state.flowchart_dot_path = None

        if 'flowchart_html_path' not in st.session_state:
            st.session_state.flowchart_html_path = None

        if 'report_path' not in st.session_state:
            st.session_state.report_path = None

        if 'parsed_clusters' not in st.session_state:
            st.session_state.parsed_clusters = None

        if 'excel_report_path' not in st.session_state:
            st.session_state.excel_report_path = None

        if 'excel_error' not in st.session_state:
            st.session_state.excel_error = None

        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = "llm_output"

        # History navigation state
        if 'view_mode' not in st.session_state:
            st.session_state.view_mode = 'new_run'

        if 'current_history_session_id' not in st.session_state:
            st.session_state.current_history_session_id = None

        if 'show_save_dialog' not in st.session_state:
            st.session_state.show_save_dialog = False

        if 'history_agent_prompt' not in st.session_state:
            st.session_state.history_agent_prompt = ""

        if 'history_fsm_instructions' not in st.session_state:
            st.session_state.history_fsm_instructions = ""

        if 'history_run_metadata' not in st.session_state:
            st.session_state.history_run_metadata = None

        if 'delete_confirmation_session_id' not in st.session_state:
            st.session_state.delete_confirmation_session_id = None

        if 'run_saved_to_history' not in st.session_state:
            st.session_state.run_saved_to_history = False

    @staticmethod
    def reset():
        """
        Reset session state and create new session ID.

        Cleanup Process:
            1. Check if current session is unsaved (not in registry)
            2. If unsaved, delete outputs/{session_id}/ directory
            3. Generate new session ID
            4. Reset all state variables
        """
        # Import here to avoid circular dependency
        from utils.history_manager import HistoryManager

        # Cleanup old session if not saved
        old_session_id = st.session_state.get('session_id')
        if old_session_id:
            history_manager = HistoryManager()
            if not history_manager.is_session_saved(old_session_id):
                # Session not in registry - safe to delete
                old_session_dir = Path(f"outputs/{old_session_id}")
                if old_session_dir.exists():
                    try:
                        shutil.rmtree(old_session_dir)
                        print(f"INFO: Cleaned up unsaved session: {old_session_id}")
                    except Exception as e:
                        # Non-fatal - don't block reset
                        print(f"WARNING: Failed to cleanup session {old_session_id}: {e}")

        # Generate new session ID
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.pipeline_running = False
        st.session_state.current_step = 0
        st.session_state.thinking_text = ""
        st.session_state.output_text = ""
        st.session_state.output_json = None
        st.session_state.cost_metrics = None
        st.session_state.flowchart_png_path = None
        st.session_state.flowchart_dot_path = None
        st.session_state.flowchart_html_path = None
        st.session_state.report_path = None
        st.session_state.parsed_clusters = None
        st.session_state.excel_report_path = None
        st.session_state.excel_error = None
        st.session_state.active_tab = "llm_output"

        # Clear history state
        st.session_state.current_history_session_id = None
        st.session_state.history_agent_prompt = ""
        st.session_state.history_fsm_instructions = ""
        st.session_state.history_run_metadata = None
        st.session_state.show_save_dialog = False
        st.session_state.delete_confirmation_session_id = None
        st.session_state.run_saved_to_history = False

        # Preserve view_mode unless in history_detail
        if st.session_state.view_mode == 'history_detail':
            st.session_state.view_mode = 'new_run'
