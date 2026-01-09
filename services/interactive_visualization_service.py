import subprocess
import sys
import os
import shutil


class InteractiveVisualizationService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def create_interactive_flowchart(self, json_data):
        """
        Wrapper around script_viz_interactive.py using subprocess for process isolation.

        Args:
            json_data: FSM transitions JSON (not used directly, reads from output.json)

        Returns:
            str: Absolute path to interactive HTML file

        Note: This is non-fatal - errors are logged but pipeline continues
        """
        try:
            # Get session directory path
            session_dir = os.path.dirname(self.file_manager.get_path('dummy'))

            # Calculate absolute path to script (project root)
            project_root = os.path.dirname(os.path.dirname(session_dir))
            script_path = os.path.join(project_root, 'script_viz_interactive.py')

            # Ensure paths are absolute (defensive)
            script_path = os.path.abspath(script_path)
            session_dir = os.path.abspath(session_dir)

            # Check that output.json exists (expected by script_viz_interactive.py)
            output_json_path = os.path.join(session_dir, 'output.json')
            if not os.path.exists(output_json_path):
                raise RuntimeError(
                    "output.json not found. Run FSM generation (script 1) first."
                )

            # Run subprocess
            try:
                subprocess.run(
                    [sys.executable, script_path],
                    cwd=session_dir,
                    check=True,
                    timeout=180,
                    capture_output=True,
                    text=True
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"Interactive visualization timed out after 180 seconds."
                ) from e
            except subprocess.CalledProcessError as e:
                # Save diagnostic info for debugging
                self.file_manager.save_json(json_data, 'failed_interactive_input.json')
                raise RuntimeError(
                    f"Interactive visualization subprocess failed with exit code {e.returncode}.\n"
                    f"stderr: {e.stderr}\n"
                    f"stdout: {e.stdout}"
                ) from e

            # Read output from session directory
            flowchart_html_path = os.path.join(session_dir, 'flowchart_interactive.html')

            if not os.path.exists(flowchart_html_path):
                raise RuntimeError(
                    "Script did not generate flowchart_interactive.html. "
                    "Interactive visualization may have failed."
                )

            # Move to final session path (already in session dir, so just return path)
            session_html = self.file_manager.get_path('flowchart_interactive.html')

            # File should already be at the right location, but if not, move it
            if flowchart_html_path != session_html:
                shutil.move(flowchart_html_path, session_html)

            return session_html

        except Exception as e:
            # Save diagnostic info for debugging
            self.file_manager.save_json(json_data, 'failed_interactive_input.json')
            # Re-raise - error handling happens in caller (app.py)
            raise RuntimeError(f"Interactive visualization failed: {str(e)}") from e
