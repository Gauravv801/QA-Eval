"""
History Service - Business logic layer for run history management.

Migrated to use Supabase for persistent storage (database + object storage).
Provides high-level operations for saving and loading historical runs.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import shutil
import tempfile

from utils.history_manager import HistoryManager
from utils.database_client import DatabaseClient
from utils.file_manager import FileManager
from services.report_parser import ReportParser, MinimalPriorityStats


class HistoryService:
    """High-level service for managing run history with Supabase."""

    def __init__(self, file_manager: Optional[FileManager] = None):
        """
        Initialize HistoryService.

        Args:
            file_manager: Optional FileManager for current session operations
        """
        self.history_manager = HistoryManager()
        self.file_manager = file_manager
        self.supabase = DatabaseClient.get_client()

    def save_current_run(
        self,
        session_id: str,
        agent_prompt: str,
        fsm_instructions: str,
        notes: str,
        cost_metrics: dict,
        parsed_clusters: list
    ) -> dict:
        """
        Save current run to Supabase database and storage.

        Process:
            1. Validate session directory exists in outputs/
            2. Upload binary files (PNG, XLSX) to Supabase Storage
            3. Insert all data into database
            4. Delete local outputs/{session_id}/ directory

        Args:
            session_id: UUID session identifier
            agent_prompt: Voice agent system prompt (full text)
            fsm_instructions: FSM extraction instructions (full text)
            notes: User-entered notes/comments
            cost_metrics: Dictionary with 'total_cost_usd', etc.
            parsed_clusters: List of Cluster objects from ReportParser

        Raises:
            RuntimeError: If session directory doesn't exist or upload fails
        """
        # Validate source directory exists
        source_dir = Path(f"outputs/{session_id}")
        if not source_dir.exists():
            raise RuntimeError(
                f"Session directory not found: {source_dir}. "
                "Cannot save run without completed session outputs."
            )

        # Load all artifacts from local session
        fm = FileManager(session_id, base_location='outputs')

        try:
            # Load text/JSON data
            output_json = fm.load_json('output.json')
            flowchart_dot = fm.load_text('flowchart_source')
            report_text = fm.load_text('clustered_flow_report.txt')

            # Load optional thinking text (not available in subprocess mode)
            try:
                thinking_text = fm.load_text('thinking.txt')
            except FileNotFoundError:
                thinking_text = ""  # Empty if not available

            # Load optional raw response
            try:
                raw_response = fm.load_text('raw_response.txt')
            except FileNotFoundError:
                raw_response = None

            # Upload binary files to Supabase Storage
            flowchart_png_path = self._upload_file(
                session_id,
                source_dir / 'flowchart.png',
                'flowchart.png'
            )

            # Upload interactive HTML
            flowchart_html_path = self._upload_file(
                session_id,
                source_dir / 'flowchart_interactive.html',
                'flowchart_interactive.html'
            )

            # Upload Excel if exists
            excel_path_local = source_dir / 'clustered_flow_report.xlsx'
            if excel_path_local.exists():
                excel_report_path = self._upload_file(
                    session_id,
                    excel_path_local,
                    'report.xlsx'
                )
            else:
                excel_report_path = None

            # Compute metadata - handle four formats: MinimalPriorityStats, stats dict, PriorityPathCollection, List[Cluster]
            if isinstance(parsed_clusters, MinimalPriorityStats):
                # New wrapped format: MinimalPriorityStats object
                num_archetypes = parsed_clusters.stats['p0_count']
                num_total_paths = (
                    parsed_clusters.stats['p0_count'] +
                    parsed_clusters.stats['p1_count'] +
                    parsed_clusters.stats['p2_count'] +
                    parsed_clusters.stats['p3_count']
                )
            elif isinstance(parsed_clusters, dict):
                # Fallback: raw stats dict (backward compatibility)
                num_archetypes = parsed_clusters['p0_count']
                num_total_paths = (
                    parsed_clusters['p0_count'] +
                    parsed_clusters['p1_count'] +
                    parsed_clusters['p2_count'] +
                    parsed_clusters['p3_count']
                )
            elif hasattr(parsed_clusters, 'stats'):
                # PriorityPathCollection object
                num_archetypes = parsed_clusters.stats['p0_count']
                num_total_paths = (
                    parsed_clusters.stats['p0_count'] +
                    parsed_clusters.stats['p1_count'] +
                    parsed_clusters.stats['p2_count'] +
                    parsed_clusters.stats['p3_count']
                )
            else:
                # Legacy format (List[Cluster])
                num_archetypes = len(parsed_clusters)
                num_total_paths = sum(
                    1 + len(c.p1_paths) + len(c.p2_paths)
                    for c in parsed_clusters
                )

            metadata = {
                "session_id": session_id,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "agent_prompt_preview": agent_prompt[:100] if len(agent_prompt) > 100 else agent_prompt,
                "fsm_instructions_preview": fsm_instructions[:100] if len(fsm_instructions) > 100 else fsm_instructions,
                "notes": notes,
                "total_cost_usd": float(cost_metrics.get('total_cost_usd', 0.0)),
                "num_archetypes": num_archetypes,
                "num_total_paths": num_total_paths,
                # Full text fields
                "agent_prompt_full": agent_prompt,
                "fsm_instructions_full": fsm_instructions,
                "output_json": output_json,
                "cost_metrics": cost_metrics,
                "thinking_text": thinking_text,
                "raw_response_text": raw_response,
                "flowchart_dot_source": flowchart_dot,
                "clustered_flow_report": report_text,
                # File references
                "flowchart_png_path": flowchart_png_path,
                "flowchart_html_path": flowchart_html_path,
                "excel_report_path": excel_report_path
            }

            # Insert into database
            self.history_manager.add_run(metadata)

            # Cleanup: Delete local outputs directory
            shutil.rmtree(source_dir)

            # Return Supabase URLs and text content for session state update
            return {
                'flowchart_png_path': flowchart_png_path,      # Supabase URL
                'flowchart_html_path': flowchart_html_path,    # Supabase URL
                'flowchart_dot_path': flowchart_dot,            # Text content (DOT source)
                'report_text': report_text,                     # Text content (clustered report)
                'excel_report_path': excel_report_path          # Supabase URL or None
            }

        except Exception as e:
            raise RuntimeError(
                f"Failed to save run to database: {str(e)}"
            ) from e

    def _upload_file(self, session_id: str, local_path: Path, filename: str) -> str:
        """
        Upload file to Supabase Storage and return public URL.

        Args:
            session_id: Session identifier (used as folder)
            local_path: Local file path
            filename: Target filename in storage

        Returns:
            Public URL to uploaded file

        Raises:
            Exception: If upload fails
        """
        storage_path = f"{session_id}/{filename}"

        with open(local_path, 'rb') as f:
            file_data = f.read()

        # Upload to Supabase Storage
        response = self.supabase.storage.from_('run-artifacts').upload(
            storage_path,
            file_data,
            file_options={
                "contentType": self._get_mime_type(filename),  # camelCase for Supabase SDK
                "cacheControl": "3600",
                "upsert": "true"
            }
        )

        # Get public URL
        public_url = self.supabase.storage.from_('run-artifacts').get_public_url(storage_path)

        return public_url

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename extension."""
        if filename.endswith('.png'):
            return 'image/png'
        elif filename.endswith('.html'):
            return 'text/html'
        elif filename.endswith('.xlsx'):
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            return 'application/octet-stream'

    def load_run_data(self, session_id: str) -> dict:
        """
        Load all session data from database.

        Args:
            session_id: UUID session identifier

        Returns:
            Dictionary containing all run data (same structure as before)

        Raises:
            FileNotFoundError: If session not found in database
        """
        # Load from database
        run_data = self.history_manager.get_run(session_id)

        if not run_data:
            raise FileNotFoundError(
                f"Session not found in database: {session_id}. "
                "The run may have been deleted."
            )

        # Parse clustered flow report from text
        # Create temp file for parser (it expects a file path)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write(run_data['clustered_flow_report'])
            report_path = tmp.name

        # Auto-detect format from report text
        report_text = run_data['clustered_flow_report']
        is_priority_mode = '=== [P0] GOLDEN PATHS' in report_text  # New format marker

        if is_priority_mode:
            # New priority-based format
            from services.report_parser import PriorityReportParser
            parser = PriorityReportParser(report_path)
            parsed_clusters = parser.parse()
        else:
            # Legacy archetype-based format
            parsed_clusters = ReportParser(report_path).parse()

        # Return data in expected format
        return {
            'output_json': run_data['output_json'],
            'cost_metrics': run_data['cost_metrics'],
            'thinking_text': run_data['thinking_text'],
            'flowchart_png_path': run_data.get('flowchart_png_path'),  # Public URL
            'flowchart_html_path': run_data.get('flowchart_html_path'),  # Public URL
            'flowchart_dot_path': run_data['flowchart_dot_source'],  # Text content
            'report_path': report_path,  # Temp file path
            'excel_report_path': run_data.get('excel_report_path'),  # Public URL
            'parsed_clusters': parsed_clusters,
            'is_priority_mode': is_priority_mode,  # NEW: Critical for rendering
            'agent_prompt': run_data['agent_prompt_full'],
            'fsm_instructions': run_data['fsm_instructions_full']
        }

    def get_history_table_data(self) -> list[dict]:
        """
        Get all runs formatted for table display.

        Returns:
            List of run metadata dictionaries (newest first)
        """
        return self.history_manager.get_all_runs()

    def delete_run_with_cleanup(self, session_id: str) -> None:
        """
        Delete run from database and remove files from Storage.

        Args:
            session_id: UUID session identifier

        Raises:
            RuntimeError: If deletion fails
        """
        # Get run data to find file paths
        run_data = self.history_manager.get_run(session_id)

        if not run_data:
            raise RuntimeError(
                f"Run with session_id {session_id} not found in database."
            )

        # Delete files from Storage
        try:
            # Delete PNG
            if run_data.get('flowchart_png_path'):
                self.supabase.storage.from_('run-artifacts').remove([
                    f"{session_id}/flowchart.png"
                ])

            # Delete HTML
            if run_data.get('flowchart_html_path'):
                self.supabase.storage.from_('run-artifacts').remove([
                    f"{session_id}/flowchart_interactive.html"
                ])

            # Delete Excel
            if run_data.get('excel_report_path'):
                self.supabase.storage.from_('run-artifacts').remove([
                    f"{session_id}/report.xlsx"
                ])
        except Exception as e:
            print(f"WARNING: Failed to delete storage files: {e}")

        # Delete from database
        deleted = self.history_manager.delete_run(session_id)

        if not deleted:
            raise RuntimeError(
                f"Failed to delete run from database: {session_id}"
            )
