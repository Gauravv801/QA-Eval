from script_2_viz import generate_flowchart
import shutil


class VisualizationService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def create_flowchart(self, json_data):
        """
        Wrapper around script_2_viz.generate_flowchart with session-based output.

        Returns:
            tuple: (png_path, dot_source_path)
        """
        # Generate flowchart in temp location
        temp_base = f"temp_flowchart_{self.file_manager.session_id}"

        try:
            png_path, dot_source_path = generate_flowchart(json_data, temp_base)
        except Exception as e:
            # Save diagnostic info for debugging
            self.file_manager.save_json(json_data, 'failed_visualization_input.json')
            raise RuntimeError(f"Flowchart generation failed: {str(e)}") from e

        # Move to session directory
        session_png = self.file_manager.get_path('flowchart.png')
        session_dot = self.file_manager.get_path('flowchart_source')

        shutil.move(png_path, session_png)
        shutil.move(dot_source_path, session_dot)

        return session_png, session_dot
