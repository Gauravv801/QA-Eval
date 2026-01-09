import streamlit as st
import time
import re
from dotenv import load_dotenv

# Load environment variables from .env file (must be before other imports)
load_dotenv()

from utils.session_state import SessionStateManager
from utils.file_manager import FileManager
from services.streaming_service import StreamingService
from services.visualization_service import VisualizationService
from services.interactive_visualization_service import InteractiveVisualizationService
from services.analysis_service import AnalysisService
from services.excel_service import ExcelService
from services.report_parser import ReportParser
from services.history_service import HistoryService
from components.execution_zone import render_thinking_console
from components.analysis_zone import render_analysis_zone
from components.visual_zone import render_visual_zone
from components.interactive_zone import render_interactive_zone
from components.results_zone import render_results_zone_priority
from components.top_navigation import render_top_navigation
from components.history_table import render_history_table, format_datetime
from components.save_dialog import show_save_dialog

# Fixed header for system prompt input
SYSTEM_PROMPT_HEADER = "## System Prompt\n"

def normalize_line_breaks(text: str) -> str:
    """
    Normalize line breaks in text to have at most one blank line between paragraphs.

    Replaces 3+ consecutive newlines with exactly 2 newlines (one blank line).

    Args:
        text: Input text with potentially excessive blank lines

    Returns:
        Text with normalized line breaks
    """
    # Replace 3 or more consecutive newlines with exactly 2 newlines
    normalized = re.sub(r'\n{3,}', '\n\n', text)
    return normalized

@st.cache_data
def load_default_fsm_instructions():
    """Load FSM extraction instructions from prompt.txt (before ---SEP---)"""
    try:
        with open('prompt.txt', 'r') as f:
            content = f.read()
            if '---SEP---' in content:
                return content.split('---SEP---')[0].strip()
    except FileNotFoundError:
        pass
    # Fallback if prompt.txt not found
    return "# Role\nYou are an expert AI Architecture Analyst and Formal Logic Extractor..."

# Page configuration (must be first Streamlit command)
st.set_page_config(page_title="QA Evaluation Pipeline")

# Initialize session state (must be before components that use it)
SessionStateManager.initialize()

# Route based on view mode
if st.session_state.view_mode == 'history_table':
    # HISTORY TABLE VIEW
    render_top_navigation()
    st.title("Run History")
    render_history_table()

elif st.session_state.view_mode == 'history_detail':
    # HISTORICAL RUN DETAIL VIEW (read-only)
    render_top_navigation()
    st.title("QA Evaluation Pipeline - Historical Run")

    history_service = HistoryService()
    try:
        run_data = history_service.load_run_data(
            st.session_state.current_history_session_id
        )

        # Populate session state with historical data
        st.session_state.output_json = run_data['output_json']
        st.session_state.cost_metrics = run_data['cost_metrics']
        st.session_state.thinking_text = run_data['thinking_text']
        st.session_state.flowchart_png_path = run_data['flowchart_png_path']
        st.session_state.flowchart_dot_path = run_data['flowchart_dot_path']
        st.session_state.flowchart_html_path = run_data.get('flowchart_html_path')
        st.session_state.report_path = run_data['report_path']
        st.session_state.parsed_clusters = run_data['parsed_clusters']
        st.session_state.is_priority_mode = run_data['is_priority_mode']  # NEW: Set format flag
        st.session_state.excel_report_path = run_data.get('excel_report_path')
        st.session_state.agent_prompt = run_data.get('agent_prompt', '')
        st.session_state.fsm_instructions = run_data.get('fsm_instructions', '')

        # Load metadata for banner
        metadata = history_service.history_manager.get_run(
            st.session_state.current_history_session_id
        )

        # Display metadata banner
        if metadata:
            st.info(
                f"Saved: {format_datetime(metadata['saved_at'])} | "
                f"Cost: ${metadata['total_cost_usd']:.4f} | "
                f"P0s: {metadata['num_archetypes']} | "
                f"Paths: {metadata['num_total_paths']} | "
                f"Notes: {metadata.get('notes', 'None')}"
            )

        # Display input prompts (collapsible)
        with st.expander("📋 FSM Extraction Instructions", expanded=False):
            st.text_area(
                label="FSM Instructions",
                value=st.session_state.get('fsm_instructions', 'No FSM instructions available'),
                height=200,
                disabled=True,
                label_visibility="collapsed"
            )

        with st.expander("🤖 Voice Agent System Prompt", expanded=False):
            st.text_area(
                label="Agent Prompt",
                value=st.session_state.get('agent_prompt', 'No agent prompt available'),
                height=300,
                disabled=True,
                label_visibility="collapsed"
            )

        # Render 4-tab interface (reuse existing components)
        tab1, tab2, tab3, tab4 = st.tabs(["LLM Output", "Flowchart", "Interactive", "Clustered Paths"])

        with tab1:
            if st.session_state.thinking_text:
                render_thinking_console(st.session_state.thinking_text,
                                       container_id="historical-thinking")
            if st.session_state.cost_metrics:
                render_analysis_zone(st.session_state.cost_metrics,
                                    st.session_state.output_json)

        with tab2:
            if st.session_state.flowchart_png_path:
                render_visual_zone(st.session_state.flowchart_png_path,
                                  st.session_state.flowchart_dot_path)

        with tab3:
            if st.session_state.flowchart_html_path:
                render_interactive_zone(st.session_state.flowchart_html_path)
            else:
                st.info("Interactive visualization not available for this run.")

        with tab4:
            if st.session_state.parsed_clusters:
                render_results_zone_priority(st.session_state.parsed_clusters,
                                            st.session_state.report_path)

    except FileNotFoundError:
        st.error("Run data not found. Directory may have been deleted.")
        if st.button("Return to History"):
            st.session_state.view_mode = 'history_table'
            st.rerun()
    except Exception as e:
        st.error(f"Failed to load: {str(e)}")
        if st.button("Return to History"):
            st.session_state.view_mode = 'history_table'
            st.rerun()

else:
    # NEW RUN VIEW (existing pipeline logic)
    render_top_navigation()
    st.title("QA Evaluation Pipeline")

    st.subheader("1. FSM Extraction Instructions")
    st.caption("System instructions that tell Claude how to extract the FSM (auto-loaded from prompt.txt)")

    fsm_instructions = st.text_area(
        label="FSM Extraction Instructions",
        value=load_default_fsm_instructions(),
        height=200,
        disabled=st.session_state.pipeline_running,
        label_visibility="collapsed"
    )

    st.subheader("2. Voice Agent System Prompt to Analyze")
    st.caption("Paste the voice agent system prompt you want to convert into an FSM")

    # Display fixed header (read-only)
    st.markdown("```markdown\n## System Prompt\n```")
    st.caption("⬆️ This header is automatically included and cannot be edited")

    # User input area (editable)
    user_prompt_content = st.text_area(
        label="Voice Agent System Prompt Content",
        height=300,
        placeholder="You are **AgentName**, an AI assistant...\n\n[Paste your voice agent system prompt content here]",
        disabled=st.session_state.pipeline_running,
        label_visibility="collapsed",
        key="user_prompt_input"
    )

    # Combine fixed header with user content
    agent_prompt = SYSTEM_PROMPT_HEADER + user_prompt_content

    col1, col2 = st.columns([2, 5])
    with col1:
        generate_button = st.button("Generate Test Cases", type="primary", disabled=st.session_state.pipeline_running)
    with col2:
        if st.button("Reset", disabled=st.session_state.pipeline_running):
            SessionStateManager.reset()
            st.rerun()

    # Pipeline execution
    if generate_button:
        # Validate both inputs are present
        if not fsm_instructions.strip():
            st.error("FSM Extraction Instructions cannot be empty")
        elif not user_prompt_content.strip():
            st.error("Voice Agent System Prompt content cannot be empty")
        else:
            # Use fsm_instructions as system prompt and agent_prompt as user message
            sys_prompt = fsm_instructions.strip()
            user_msg = agent_prompt.strip()

            # Initialize services
            st.session_state.pipeline_running = True
            file_manager = FileManager(st.session_state.session_id)

            # Save input prompts for historical retrieval
            file_manager.save_text(agent_prompt, 'agent_prompt.txt')
            file_manager.save_text(fsm_instructions, 'fsm_instructions.txt')

            # Store for save dialog
            st.session_state.last_agent_prompt = agent_prompt
            st.session_state.last_fsm_instructions = fsm_instructions

            # STEP 1: Generation
            st.session_state.current_step = 1

            thinking_container = st.empty()
            last_update_time = [0]  # Use list to allow mutation in nested function

            def on_thinking_update(chunk, full_thinking):
                st.session_state.thinking_text = full_thinking

                # Throttle: Update UI at most every 200ms
                current_time = time.time()
                if current_time - last_update_time[0] >= 0.2:
                    with thinking_container:
                        container_id = f"thinking-console-{int(current_time * 1000)}"
                        render_thinking_console(full_thinking, container_id=container_id)
                    last_update_time[0] = current_time

            streaming_service = StreamingService(file_manager)

            with st.spinner("Generating FSM..."):
                try:
                    json_data, cost_data = streaming_service.stream_generation(
                        sys_prompt,
                        user_msg,
                        thinking_callback=on_thinking_update
                    )
                    st.session_state.output_json = json_data
                    st.session_state.cost_metrics = cost_data

                    # Final render with complete thinking
                    with thinking_container:
                        render_thinking_console(st.session_state.thinking_text, container_id="thinking-console-final")

                except ValueError as e:
                    st.error(f"**Generation Failed**: {str(e)}")
                    st.warning(
                        "**Troubleshooting Steps:**\n"
                        "1. Check that your system prompt requests JSON output\n"
                        "2. Review the thinking process above for clues\n"
                        f"3. Inspect debug files in `outputs/{st.session_state.session_id}/`"
                    )
                    st.session_state.pipeline_running = False
                    st.stop()  # Stop execution but keep UI state

                except Exception as e:
                    st.error(f"**Unexpected Error**: {str(e)}")
                    st.session_state.pipeline_running = False
                    st.stop()

            # STEP 2: Visualization
            st.session_state.current_step = 2

            viz_service = VisualizationService(file_manager)

            with st.spinner("Creating flowchart..."):
                png_path, dot_path = viz_service.create_flowchart(json_data)
                st.session_state.flowchart_png_path = png_path
                st.session_state.flowchart_dot_path = dot_path

            # STEP 2B: Interactive Visualization
            interactive_viz_service = InteractiveVisualizationService(file_manager)

            with st.spinner("Creating interactive flowchart..."):
                try:
                    html_path = interactive_viz_service.create_interactive_flowchart(json_data)
                    st.session_state.flowchart_html_path = html_path
                    st.session_state.interactive_error = None # Clear previous errors
                except Exception as e:
                    st.session_state.flowchart_html_path = None
                    st.session_state.interactive_error = str(e) # Persist error

            # STEP 3: Analysis
            st.session_state.current_step = 3

            analysis_service = AnalysisService(file_manager)

            with st.spinner("Analyzing conversation paths..."):
                # NEW: analyze_paths now returns tuple (priority_collection, report_path)
                priority_collection, report_path = analysis_service.analyze_paths(dot_path)

                st.session_state.report_path = report_path
                st.session_state.parsed_clusters = priority_collection  # Now PriorityPathCollection
                st.session_state.is_priority_mode = True  # Flag for rendering

                # Generate Excel report using new priority method
                excel_service = ExcelService(file_manager)
                try:
                    excel_path = excel_service.generate_excel_priority(
                        priority_collection,
                        st.session_state.output_json
                    )
                    st.session_state.excel_report_path = excel_path
                    st.session_state.excel_error = None  # Clear any previous error
                except Exception as e:
                    # Non-fatal: Excel generation failure shouldn't block pipeline
                    # Store error for display after rerun
                    st.session_state.excel_error = str(e)
                    st.session_state.excel_report_path = None

            st.session_state.pipeline_running = False
            st.success("Pipeline complete!")
            st.rerun()

    # Save to History button (shown after pipeline completes)
    if (st.session_state.current_step == 3 and
        not st.session_state.pipeline_running and
        st.session_state.parsed_clusters):

        st.markdown("---")

        # Show success message if already saved, otherwise show button
        if st.session_state.run_saved_to_history:
            st.success(f"✓ Run saved to history")
        else:
            if st.button("Save to History", type="secondary"):
                st.session_state.show_save_dialog = True
                st.rerun()

    # Tabbed Results Display (visible immediately after clicking Generate)
    if st.session_state.pipeline_running or st.session_state.current_step > 0:
        tab1, tab2, tab3, tab4 = st.tabs(["LLM Output", "Flowchart", "Interactive", "Clustered Paths"])

        with tab1:
            # Thinking Console
            if st.session_state.thinking_text:
                render_thinking_console(st.session_state.thinking_text, container_id="thinking-console-static")

            # Analysis Zone (KPI + JSON)
            if st.session_state.cost_metrics:
                render_analysis_zone(st.session_state.cost_metrics, st.session_state.output_json)
            else:
                st.info("Generating FSM analysis... This may take a few moments.")

        with tab2:
            # Visual Zone (Flowchart)
            if st.session_state.flowchart_png_path:
                render_visual_zone(st.session_state.flowchart_png_path, st.session_state.flowchart_dot_path)
            else:
                st.info("Waiting for flowchart generation... Complete Step 1 first.")

        with tab3:
            # Interactive Zone (Interactive Flowchart)
            if st.session_state.get('flowchart_html_path'):
                render_interactive_zone(st.session_state.flowchart_html_path)
            elif st.session_state.get('interactive_error'):
                st.error(f"Interactive Visualization Failed: {st.session_state.interactive_error}")
            else:
                st.info("Waiting for interactive flowchart... Complete Step 1 first.")

        with tab4:
            # Results Zone (Clustered Paths)
            if st.session_state.parsed_clusters:
                render_results_zone_priority(st.session_state.parsed_clusters, st.session_state.report_path)
            else:
                st.info("Waiting for path analysis... Complete Step 2 first.")

# Show save dialog if triggered
if st.session_state.show_save_dialog and st.session_state.view_mode == 'new_run':
    show_save_dialog(
        st.session_state.session_id,
        st.session_state.get('last_agent_prompt', ''),
        st.session_state.get('last_fsm_instructions', ''),
        st.session_state.cost_metrics,
        st.session_state.parsed_clusters
    )
