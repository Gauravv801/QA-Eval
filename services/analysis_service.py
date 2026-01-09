import subprocess
import sys
import os
import shutil
import re


class AnalysisService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def analyze_paths(self, dot_source_path, start_node='STATE_GREETING', end_node='STATE_END_CONVERSATION'):
        """
        Wrapper around script_3_ana.py using subprocess for process isolation.

        Returns minimal stats dict instead of full PriorityPathCollection to reduce memory usage.
        Full path data can be parsed on-demand from the report file using PriorityReportParser.

        Args:
            dot_source_path: Path to DOT source file (flowchart_source)
            start_node: Starting state name
            end_node: Ending state name

        Returns:
            tuple: (stats_dict, report_path)
                - stats_dict: {'p0_count': int, 'p1_count': int, 'p2_count': int, 'p3_count': int}
                - report_path: str path to text report file
        """
        try:
            # Get session directory path
            session_dir = os.path.dirname(self.file_manager.get_path('dummy'))

            # Calculate absolute path to script (project root)
            project_root = os.path.dirname(os.path.dirname(session_dir))
            script_path = os.path.join(project_root, 'script_3_ana.py')

            # Ensure paths are absolute (defensive)
            script_path = os.path.abspath(script_path)
            session_dir = os.path.abspath(session_dir)

            # File bridging: Copy flowchart_source → flowchart_collections_std (expected by script_3_ana.py)
            flowchart_collections_path = os.path.join(session_dir, 'flowchart_collections_std')

            if not os.path.exists(dot_source_path):
                raise RuntimeError(
                    f"DOT source file not found at {dot_source_path}. "
                    "Run flowchart generation (script 2) first."
                )

            shutil.copy(dot_source_path, flowchart_collections_path)

            # Run subprocess
            try:
                subprocess.run(
                    [sys.executable, script_path],
                    cwd=session_dir,
                    check=True,
                    timeout=600,
                    capture_output=True,
                    text=True
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"Path analysis timed out after 600 seconds. "
                    f"This may indicate a very complex FSM graph."
                ) from e
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Path analysis subprocess failed with exit code {e.returncode}.\n"
                    f"stderr: {e.stderr}\n"
                    f"stdout: {e.stdout}"
                ) from e

            # Read report file
            report_path = self.file_manager.get_path('clustered_flow_report.txt')

            if not os.path.exists(report_path):
                raise RuntimeError(
                    "Script did not generate clustered_flow_report.txt. "
                    "Path analysis may have failed."
                )

            # Parse ONLY stats from report header (memory optimization)
            stats_dict = self._parse_stats_from_report(report_path)

            return (stats_dict, report_path)

        except RuntimeError as e:
            # Re-raise subprocess errors
            raise
        except Exception as e:
            raise RuntimeError(f"Unexpected error during path analysis: {str(e)}") from e

    def _parse_stats_from_report(self, report_path: str) -> dict:
        """
        Parse ONLY stats from report header to minimize memory usage.

        Full path data can be parsed on-demand using PriorityReportParser.

        Args:
            report_path: Path to clustered_flow_report.txt

        Returns:
            dict: {'p0_count': int, 'p1_count': int, 'p2_count': int, 'p3_count': int}
        """
        try:
            with open(report_path, 'r') as f:
                # Read only first 500 chars (stats are in header)
                header = f.read(500)

            # Extract stats using regex: P0=X | P1=Y | P2=Z | P3=W
            stats_pattern = r'P0=(\d+) \| P1=(\d+) \| P2=(\d+) \| P3=(\d+)'
            match = re.search(stats_pattern, header)

            if match:
                return {
                    'p0_count': int(match.group(1)),
                    'p1_count': int(match.group(2)),
                    'p2_count': int(match.group(3)),
                    'p3_count': int(match.group(4))
                }
            else:
                # Graceful degradation - return empty stats if parsing fails
                return {'p0_count': 0, 'p1_count': 0, 'p2_count': 0, 'p3_count': 0}

        except Exception as e:
            # Graceful degradation
            return {'p0_count': 0, 'p1_count': 0, 'p2_count': 0, 'p3_count': 0}
