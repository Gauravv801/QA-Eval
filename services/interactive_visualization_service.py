from script_viz_interactive import generate_interactive_graph
import shutil


class InteractiveVisualizationService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def create_interactive_flowchart(self, json_data):
        """
        Wrapper around script_viz_interactive.generate_interactive_graph with session-based output.

        Returns:
            str: Absolute path to interactive HTML file
        """
        # Generate flowchart in temp location
        temp_output = f"temp_interactive_{self.file_manager.session_id}.html"

        try:
            html_path = generate_interactive_graph(json_data, temp_output)
        except Exception as e:
            # Save diagnostic info for debugging
            self.file_manager.save_json(json_data, 'failed_interactive_input.json')
            raise RuntimeError(f"Interactive visualization failed: {str(e)}") from e

        # Move to session directory
        session_html = self.file_manager.get_path('flowchart_interactive.html')
        shutil.move(html_path, session_html)

        return session_html
