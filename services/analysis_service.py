from typing import List
from script_3_ana import generate_path_analysis
from services.report_parser import PriorityReportParser, PriorityPathCollection, PathSegment, PriorityPath


class AnalysisService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def analyze_paths(self, dot_source_path, start_node='STATE_GREETING', end_node='STATE_END_CONVERSATION'):
        """
        Wrapper around script_3_ana.generate_path_analysis with session-based output.

        Returns:
            tuple: (parsed_priority_collection, report_path)
                - parsed_priority_collection: PriorityPathCollection object
                - report_path: str path to text report file
        """
        report_path = self.file_manager.get_path('clustered_flow_report.txt')

        # Call script function - now returns tuple
        prioritized_dict, report_path = generate_path_analysis(dot_source_path, report_path, start_node, end_node)

        # Convert dictionary to structured data model
        parsed_collection = self._dict_to_priority_collection(prioritized_dict)

        return (parsed_collection, report_path)

    def _dict_to_priority_collection(self, prioritized_dict: dict) -> PriorityPathCollection:
        """
        Convert prioritized dictionary from script to PriorityPathCollection.

        Args:
            prioritized_dict: Dictionary with 'final_p0', 'final_p1', etc.

        Returns:
            PriorityPathCollection with structured PriorityPath objects
        """
        def _convert_path_list(path_data_list, priority_level):
            """Convert list of path_data dicts to PriorityPath objects."""
            result = []
            for i, path_data in enumerate(path_data_list, start=1):
                # path_data = {'raw': [(src, tgt, action), ...], 'signature': [...], 'length': int}
                segments = self._tuples_to_segments(path_data['raw'])
                priority_path = PriorityPath(
                    priority_level=priority_level,
                    path_index=i,
                    segments=segments,
                    length=path_data['length'],
                    raw_tuples=path_data['raw'],
                    signature=path_data['signature']
                )
                result.append(priority_path)
            return result

        return PriorityPathCollection(
            p0_paths=_convert_path_list(prioritized_dict['final_p0'], 'P0'),
            p1_paths=_convert_path_list(prioritized_dict['final_p1'], 'P1'),
            p2_paths=_convert_path_list(prioritized_dict['final_p2'], 'P2'),
            p3_paths=_convert_path_list(prioritized_dict['final_p3'], 'P3'),
            skipped_edges=prioritized_dict['skipped_edges'],
            skipped_loops=prioritized_dict['skipped_loops'],
            stats=prioritized_dict['stats']
        )

    def _tuples_to_segments(self, raw_tuples) -> List[PathSegment]:
        """Convert raw tuple format to PathSegment objects."""
        segments = []
        for src, tgt, action in raw_tuples:
            segments.append(PathSegment(
                source=src,
                target=tgt,
                action=action,
                tag=None,
                tag_type=None
            ))
        return segments
