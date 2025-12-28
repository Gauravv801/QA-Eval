"""
History Service - Business logic layer for run history management.

Provides high-level operations for saving and loading historical runs, including:
- Saving current run with computed metadata
- Loading all artifacts from a session directory
- Formatting runs for table display
- Deleting runs with directory cleanup
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from utils.history_manager import HistoryManager
from utils.file_manager import FileManager
from services.report_parser import ReportParser


class HistoryService:
    """High-level service for managing run history."""

    def __init__(self, file_manager: Optional[FileManager] = None):
        """
        Initialize HistoryService.

        Args:
            file_manager: Optional FileManager for current session operations
        """
        self.history_manager = HistoryManager()
        self.file_manager = file_manager

    def save_current_run(
        self,
        session_id: str,
        agent_prompt: str,
        fsm_instructions: str,
        notes: str,
        cost_metrics: dict,
        parsed_clusters: list
    ) -> None:
        """
        Save current run to history with directory move and metadata registry.

        Process:
            1. Validate session directory exists in outputs/
            2. Move outputs/{session_id}/ -> history/{session_id}/
            3. Add metadata to registry
            4. Rollback move if registry update fails

        Args:
            session_id: UUID session identifier
            agent_prompt: Voice agent system prompt (full text)
            fsm_instructions: FSM extraction instructions (full text)
            notes: User-entered notes/comments
            cost_metrics: Dictionary with 'total_cost_usd', 'input_tokens', etc.
            parsed_clusters: List of Cluster objects from ReportParser

        Returns:
            None

        Raises:
            RuntimeError: If session directory doesn't exist or move fails
        """
        # Validate source directory exists
        source_dir = Path(f"outputs/{session_id}")
        if not source_dir.exists():
            raise RuntimeError(
                f"Session directory not found: {source_dir}. "
                "Cannot save run without completed session outputs."
            )

        # Validate destination doesn't exist (prevent overwrites)
        dest_dir = Path(f"history/{session_id}")
        if dest_dir.exists():
            raise RuntimeError(
                f"History directory already exists: {dest_dir}. "
                "This session may have been saved previously."
            )

        # Compute metadata
        metadata = {
            "session_id": session_id,
            "saved_at": datetime.now().isoformat(),
            "agent_prompt_preview": agent_prompt[:100] if len(agent_prompt) > 100 else agent_prompt,
            "fsm_instructions_preview": fsm_instructions[:100] if len(fsm_instructions) > 100 else fsm_instructions,
            "notes": notes,
            "total_cost_usd": cost_metrics.get('total_cost_usd', 0.0),
            "num_archetypes": len(parsed_clusters),
            "num_total_paths": sum(
                1 + len(c.p1_paths) + len(c.p2_paths)
                for c in parsed_clusters
            )
        }

        # Atomic operation: Move directory, then update registry
        try:
            # Move directory to history/
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_dir), str(dest_dir))

            # Add to registry
            self.history_manager.add_run(metadata)

        except Exception as e:
            # Rollback: Move directory back to outputs if it was moved
            if dest_dir.exists() and not source_dir.exists():
                try:
                    shutil.move(str(dest_dir), str(source_dir))
                except Exception as rollback_error:
                    # Critical: Directory in limbo, log for manual intervention
                    print(f"CRITICAL: Rollback failed - directory stranded at {dest_dir}")
                    print(f"Original error: {e}")
                    print(f"Rollback error: {rollback_error}")

            raise RuntimeError(
                f"Failed to save run to history: {str(e)}. "
                "Directory move rolled back."
            ) from e

    def load_run_data(self, session_id: str) -> dict:
        """
        Load all session data from history/{session_id}/ or outputs/{session_id}/.

        Checks history/ first (saved runs), falls back to outputs/ (legacy/unsaved).

        Args:
            session_id: UUID session identifier

        Returns:
            Dictionary containing:
                - output_json: FSM structure
                - cost_metrics: API costs
                - thinking_text: Claude thinking output
                - flowchart_png_path: Path to PNG
                - flowchart_dot_path: Path to DOT source
                - report_path: Path to text report
                - parsed_clusters: List of Cluster objects
                - excel_report_path: Path to XLSX (or None)
                - agent_prompt: Original prompt text
                - fsm_instructions: Original FSM instructions

        Raises:
            FileNotFoundError: If session directory not found in either location
        """
        # Check history/ first (primary location for saved runs)
        history_dir = Path(f"history/{session_id}")
        outputs_dir = Path(f"outputs/{session_id}")

        if history_dir.exists():
            base_location = 'history'
            session_dir = history_dir
        elif outputs_dir.exists():
            base_location = 'outputs'
            session_dir = outputs_dir
            # Log warning for legacy location
            print(f"WARNING: Loading run from outputs/ (legacy location): {session_id}")
        else:
            raise FileNotFoundError(
                f"Session directory not found in history/ or outputs/: {session_id}. "
                "The run may have been deleted manually."
            )

        # Create FileManager with appropriate base location
        file_manager = FileManager(session_id, base_location=base_location)

        # Load all artifacts
        output_json = file_manager.load_json('output.json')
        cost_metrics = file_manager.load_json('cost_metrics.json')
        thinking_text = file_manager.load_text('thinking.txt')

        # Parse clustered flow report
        report_path = str(session_dir / 'clustered_flow_report.txt')
        parsed_clusters = ReportParser(report_path).parse()

        # Check if Excel file exists (non-fatal if missing)
        excel_path = session_dir / 'clustered_flow_report.xlsx'
        excel_report_path = str(excel_path) if excel_path.exists() else None

        # Load input prompts with fallback for legacy runs
        try:
            agent_prompt = file_manager.load_text('agent_prompt.txt')
        except FileNotFoundError:
            agent_prompt = '[Not available - legacy run created before prompt persistence]'

        try:
            fsm_instructions = file_manager.load_text('fsm_instructions.txt')
        except FileNotFoundError:
            fsm_instructions = '[Not available - legacy run created before prompt persistence]'

        return {
            'output_json': output_json,
            'cost_metrics': cost_metrics,
            'thinking_text': thinking_text,
            'flowchart_png_path': str(session_dir / 'flowchart.png'),
            'flowchart_dot_path': str(session_dir / 'flowchart_source'),
            'report_path': str(session_dir / 'clustered_flow_report.txt'),
            'excel_report_path': excel_report_path,
            'parsed_clusters': parsed_clusters,
            'agent_prompt': agent_prompt,
            'fsm_instructions': fsm_instructions
        }

    def get_history_table_data(self) -> list[dict]:
        """
        Get all runs formatted for table display.

        Returns:
            List of run metadata dictionaries sorted by saved_at descending (newest first)
        """
        return self.history_manager.get_all_runs()

    def delete_run_with_cleanup(self, session_id: str) -> None:
        """
        Delete run from registry AND delete session directory from history/.

        Also checks outputs/ for legacy runs and cleans up if found.

        Args:
            session_id: UUID session identifier

        Raises:
            RuntimeError: If registry deletion fails

        Note:
            Directory deletion is non-fatal - continues even if directory missing.
        """
        # Delete from registry first (fail-fast)
        deleted = self.history_manager.delete_run(session_id)

        if not deleted:
            raise RuntimeError(
                f"Run with session_id {session_id} not found in registry. "
                "Nothing to delete."
            )

        # Delete from history/ (primary location)
        history_dir = Path(f"history/{session_id}")
        if history_dir.exists():
            try:
                shutil.rmtree(history_dir)
            except Exception as e:
                print(f"WARNING: Failed to delete history directory {history_dir}: {e}")

        # Also check outputs/ for legacy runs
        outputs_dir = Path(f"outputs/{session_id}")
        if outputs_dir.exists():
            try:
                shutil.rmtree(outputs_dir)
                print(f"INFO: Cleaned up legacy directory from outputs/: {session_id}")
            except Exception as e:
                print(f"WARNING: Failed to delete outputs directory {outputs_dir}: {e}")
