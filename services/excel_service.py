import re
from typing import List
import pandas as pd
from services.report_parser import PathSegment, Cluster


def flatten_path_to_strings(segments: List[PathSegment]) -> List[str]:
    """
    Flatten PathSegment list into vertical string list.

    Args:
        segments: List of PathSegment objects (from report_parser.py)

    Returns:
        List of strings: [source_state, action, target_state, action, ...]

    Example:
        Input: [
            PathSegment(source="STATE_A", action="USER_GREET", target="STATE_B"),
            PathSegment(source="STATE_B", action="AUTO_PROCEED", target="STATE_C")
        ]
        Output: ["STATE_A", "USER_GREET", "STATE_B", "AUTO_PROCEED", "STATE_C"]
    """
    if not segments:
        return []

    result = []
    result.append(segments[0].source)  # First state

    for segment in segments:
        result.append(segment.action)   # Action
        result.append(segment.target)   # Next state

    return result


def sanitize_sheet_name(name: str) -> str:
    """
    Sanitize sheet name to comply with Excel requirements.

    Excel sheet name rules:
    - Cannot contain: [ ] : * ? / \\
    - Maximum 31 characters
    - Must have at least one character

    Args:
        name: Original sheet name

    Returns:
        str: Sanitized sheet name (guaranteed non-empty)
    """
    # Remove illegal characters: []:\*?/\\
    sanitized = re.sub(r'[\[\]:*?/\\]', '', name)

    # Ensure non-empty (fallback to generic name)
    if not sanitized or sanitized.isspace():
        sanitized = "Sheet"

    # Truncate to 31 characters (Excel limit)
    return sanitized[:31]


def build_description_lookup(vocabulary_json: dict) -> dict:
    """
    Build state/intent ID → description lookup dictionary.

    Args:
        vocabulary_json: Full output.json structure with vocabulary key

    Returns:
        dict: Mapping of state/intent IDs to their descriptions
            Example: {
                "STATE_GREETING": "Bot welcomes user",
                "USER_RESPOND_GREETING": "User responds to greeting",
                ...
            }
    """
    if not vocabulary_json or 'vocabulary' not in vocabulary_json:
        return {}

    descriptions = {}
    vocabulary = vocabulary_json.get('vocabulary', {})

    # Extract state descriptions
    states = vocabulary.get('states', [])
    for state_obj in states:
        state_id = state_obj.get('id')
        state_desc = state_obj.get('description', '')
        if state_id:
            descriptions[state_id] = state_desc

    # Extract intent descriptions
    intents = vocabulary.get('intents', [])
    for intent_obj in intents:
        intent_id = intent_obj.get('id')
        intent_desc = intent_obj.get('description', '')
        if intent_id:
            descriptions[intent_id] = intent_desc

    return descriptions


def flatten_path_with_descriptions(
    segments: List[PathSegment],
    description_lookup: dict
) -> tuple:
    """
    Flatten PathSegment list into parallel vertical lists: flow + descriptions.

    Args:
        segments: List of PathSegment objects
        description_lookup: Dict mapping state/intent IDs to descriptions

    Returns:
        tuple: (flow_list, description_list)
            - flow_list: ["STATE_A", "USER_GREET", "STATE_B", ...]
            - description_list: ["Bot welcomes...", "User responds...", "Bot asks...", ...]

    Example:
        Input segments: [PathSegment(source="STATE_A", action="USER_X", target="STATE_B")]
        Input lookup: {"STATE_A": "Desc A", "USER_X": "Desc X", "STATE_B": "Desc B"}
        Output: (
            ["STATE_A", "USER_X", "STATE_B"],
            ["Desc A", "Desc X", "Desc B"]
        )
    """
    if not segments:
        return ([], [])

    flow_list = []
    desc_list = []

    # Add first source state
    source_id = segments[0].source
    flow_list.append(source_id)
    desc_list.append(description_lookup.get(source_id, ""))

    # Add action and target for each segment
    for segment in segments:
        # Add action
        action_id = segment.action
        flow_list.append(action_id)
        desc_list.append(description_lookup.get(action_id, ""))

        # Add target state
        target_id = segment.target
        flow_list.append(target_id)
        desc_list.append(description_lookup.get(target_id, ""))

    return (flow_list, desc_list)


class ExcelService:
    """
    Service for generating Excel (.xlsx) reports from conversation clustering data.

    Follows the established service pattern (AnalysisService, VisualizationService)
    with FileManager integration for session-isolated file operations.
    """

    def __init__(self, file_manager):
        """
        Initialize ExcelService with FileManager instance.

        Args:
            file_manager: FileManager instance for session-isolated file operations
        """
        self.file_manager = file_manager

    def generate_excel(self, clusters: List[Cluster], vocabulary_json: dict = None) -> str:
        """
        Generate Excel file with one sheet per P0 archetype.

        Args:
            clusters: List[Cluster] objects from report parser
            vocabulary_json: Optional dict from output.json with vocabulary.states/intents

        Returns:
            str: Absolute path to generated .xlsx file

        Raises:
            ValueError: If clusters is empty or invalid
            RuntimeError: If Excel generation fails
        """
        if not clusters:
            raise ValueError("No clusters provided for Excel export")

        output_path = self.file_manager.get_path('clustered_flow_report.xlsx')

        try:
            return self._create_excel_from_clusters(clusters, output_path, vocabulary_json)
        except Exception as e:
            raise RuntimeError(f"Excel generation failed: {str(e)}") from e

    def _create_excel_from_clusters(self, clusters: List[Cluster], output_path: str, vocabulary_json: dict = None) -> str:
        """
        Internal method to create Excel workbook from clusters with descriptions.

        Args:
            clusters: List[Cluster] objects
            output_path: Full path where Excel file should be saved
            vocabulary_json: Optional vocabulary data for descriptions

        Returns:
            str: Path to saved Excel file
        """
        # Build description lookup dictionary
        description_lookup = build_description_lookup(vocabulary_json) if vocabulary_json else {}

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for cluster in clusters:
                # Build dictionary for DataFrame with interleaved columns
                data = {}
                all_column_names = []  # Track column order

                # Add P0 columns (flow + description + blank separator)
                p0_flow, p0_desc = flatten_path_with_descriptions(cluster.p0_path.segments, description_lookup)
                data['P0'] = p0_flow
                data['P0_Desc'] = p0_desc
                data['P0_Blank'] = [None] * len(p0_flow)
                all_column_names.extend(['P0', 'P0_Desc', 'P0_Blank'])

                # Add P1 columns (flow + description + blank for each)
                for i, p1_path in enumerate(cluster.p1_paths, start=1):
                    col_flow = f'P1.{i}'
                    col_desc = f'P1.{i}_Desc'
                    col_blank = f'P1.{i}_Blank'

                    p1_flow, p1_desc = flatten_path_with_descriptions(p1_path.segments, description_lookup)
                    data[col_flow] = p1_flow
                    data[col_desc] = p1_desc
                    data[col_blank] = [None] * len(p1_flow)

                    all_column_names.extend([col_flow, col_desc, col_blank])

                # Add P2 columns (flow + description + blank for each)
                for i, p2_path in enumerate(cluster.p2_paths, start=1):
                    col_flow = f'P2.{i}'
                    col_desc = f'P2.{i}_Desc'
                    col_blank = f'P2.{i}_Blank'

                    p2_flow, p2_desc = flatten_path_with_descriptions(p2_path.segments, description_lookup)
                    data[col_flow] = p2_flow
                    data[col_desc] = p2_desc
                    data[col_blank] = [None] * len(p2_flow)

                    all_column_names.extend([col_flow, col_desc, col_blank])

                # Pad all columns to the same length with None values
                if data:  # Ensure data is not empty
                    max_length = max(len(col) for col in data.values())
                    for col_name in data:
                        current_length = len(data[col_name])
                        if current_length < max_length:
                            # Pad with None values to match max_length
                            data[col_name] = data[col_name] + [None] * (max_length - current_length)

                # Create DataFrame with explicit column order (preserves interleaving)
                df = pd.DataFrame(data, columns=all_column_names)

                # Sheet name
                sheet_name = sanitize_sheet_name(f"Archetype {cluster.archetype_id}")

                # Write to Excel (index=False prevents row numbers)
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        return output_path

    def generate_excel_priority(self, priority_collection, vocabulary_json: dict = None) -> str:
        """
        Generate Excel file with 4 priority tabs (P0: Base Paths, P1: Logic Variations, P2: Loops, P3: Supplemental).

        Args:
            priority_collection: PriorityPathCollection object
            vocabulary_json: Optional dict from output.json with vocabulary

        Returns:
            str: Absolute path to generated .xlsx file

        Raises:
            ValueError: If priority_collection is empty or invalid
            RuntimeError: If Excel generation fails
        """
        if not priority_collection:
            raise ValueError("No priority collection provided for Excel export")

        output_path = self.file_manager.get_path('clustered_flow_report.xlsx')

        try:
            return self._create_excel_from_priority(priority_collection, output_path, vocabulary_json)
        except Exception as e:
            raise RuntimeError(f"Excel generation failed: {str(e)}") from e

    def _create_excel_from_priority(self, priority_collection, output_path: str, vocabulary_json: dict = None) -> str:
        """
        Internal method to create Excel workbook with 4 tabs.

        Tab structure:
        - P0_Base_Paths: Columns [Flow, Description, Blank, Flow, Description, Blank, ...]
        - P1_Logic_Variations: Same structure
        - P2_Loops: Same structure
        - P3_Supplemental: Same structure
        """
        description_lookup = build_description_lookup(vocabulary_json) if vocabulary_json else {}

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Define tab configuration
            tabs_config = [
                ('P0_Base_Paths', priority_collection.p0_paths),
                ('P1_Logic_Variations', priority_collection.p1_paths),
                ('P2_Loops', priority_collection.p2_paths),
                ('P3_Supplemental', priority_collection.p3_paths)
            ]

            for tab_name, path_list in tabs_config:
                data = {}
                all_column_names = []

                # Add columns for each path (Flow + Description + Blank separator)
                for priority_path in path_list:
                    col_prefix = f"{priority_path.priority_level}.{priority_path.path_index}"
                    col_flow = col_prefix
                    col_desc = f"{col_prefix}_Desc"
                    col_blank = f"{col_prefix}_Blank"

                    # Flatten path to vertical lists
                    flow_list, desc_list = flatten_path_with_descriptions(
                        priority_path.segments,
                        description_lookup
                    )

                    data[col_flow] = flow_list
                    data[col_desc] = desc_list
                    data[col_blank] = [None] * len(flow_list)

                    all_column_names.extend([col_flow, col_desc, col_blank])

                # Pad all columns to same length
                if data:
                    max_length = max(len(col) for col in data.values())
                    for col_name in data:
                        current_length = len(data[col_name])
                        if current_length < max_length:
                            data[col_name] = data[col_name] + [None] * (max_length - current_length)

                # Create DataFrame and write
                df = pd.DataFrame(data, columns=all_column_names) if data else pd.DataFrame()
                df.to_excel(writer, sheet_name=sanitize_sheet_name(tab_name), index=False)

        return output_path
