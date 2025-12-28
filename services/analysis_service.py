from script_3_ana import generate_path_analysis


class AnalysisService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def analyze_paths(self, dot_source_path, start_node='STATE_GREETING', end_node='STATE_END_CONVERSATION'):
        """
        Wrapper around script_3_ana.generate_path_analysis with session-based output.

        Returns:
            str: Path to report file
        """
        report_path = self.file_manager.get_path('clustered_flow_report.txt')

        # Call original script function
        generate_path_analysis(dot_source_path, report_path, start_node, end_node)

        return report_path
