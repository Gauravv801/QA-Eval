import subprocess
import sys
import os
import shutil
import json


class VisualizationService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def create_flowchart(self, json_data):
        """
        Wrapper around script_2_viz.py using subprocess for process isolation.

        Args:
            json_data: FSM transitions JSON (not used directly, reads from output.json)

        Returns:
            tuple: (png_path, dot_source_path)
        """
        try:
            # Get session directory path
            session_dir = os.path.dirname(self.file_manager.get_path('dummy'))

            # Calculate absolute path to script (project root)
            project_root = os.path.dirname(os.path.dirname(session_dir))
            script_path = os.path.join(project_root, 'script_2_viz.py')

            # Ensure paths are absolute (defensive)
            script_path = os.path.abspath(script_path)
            session_dir = os.path.abspath(session_dir)

            # File bridging: Copy output.json → LLM_output_axis.json (expected by script_2_viz.py)
            output_json_path = os.path.join(session_dir, 'output.json')
            llm_output_path = os.path.join(session_dir, 'LLM_output_axis.json')

            if not os.path.exists(output_json_path):
                raise RuntimeError(
                    "output.json not found. Run FSM generation (script 1) first."
                )

            shutil.copy(output_json_path, llm_output_path)

            # Run subprocess
            try:
                subprocess.run(
                    [sys.executable, script_path],
                    cwd=session_dir,
                    check=True,
                    timeout=120,
                    capture_output=True,
                    text=True
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"Flowchart generation timed out after 120 seconds."
                ) from e
            except subprocess.CalledProcessError as e:
                # Save diagnostic info for debugging
                self.file_manager.save_json(json_data, 'failed_visualization_input.json')
                raise RuntimeError(
                    f"Flowchart generation subprocess failed with exit code {e.returncode}.\n"
                    f"stderr: {e.stderr}\n"
                    f"stdout: {e.stdout}"
                ) from e

            # Read outputs from session directory
            flowchart_png_path = os.path.join(session_dir, 'flowchart_claude.png')
            flowchart_dot_path = os.path.join(session_dir, 'flowchart_claude')

            if not os.path.exists(flowchart_png_path):
                raise RuntimeError(
                    "Script did not generate flowchart_claude.png. "
                    "Visualization may have failed."
                )
            if not os.path.exists(flowchart_dot_path):
                raise RuntimeError(
                    "Script did not generate flowchart_claude (DOT source). "
                    "Visualization may have failed."
                )

            # Move to final session paths
            session_png = self.file_manager.get_path('flowchart.png')
            session_dot = self.file_manager.get_path('flowchart_source')

            shutil.move(flowchart_png_path, session_png)
            shutil.move(flowchart_dot_path, session_dot)

            return session_png, session_dot

        except RuntimeError as e:
            # Re-raise subprocess errors
            raise
        except Exception as e:
            # Save diagnostic info for debugging
            self.file_manager.save_json(json_data, 'failed_visualization_input.json')
            raise RuntimeError(f"Unexpected error during flowchart generation: {str(e)}") from e
