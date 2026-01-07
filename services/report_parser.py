import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal


@dataclass
class PathSegment:
    source: str
    target: str
    action: str
    tag: Optional[str] = None
    tag_type: Optional[str] = None  # 'NEW', 'LOOP', 'MODIFIED', 'ACTION_CHANGED'


@dataclass
class Path:
    path_id: str
    segments: List[PathSegment]
    length: int


@dataclass
class Cluster:
    archetype_id: int
    p0_path: Path
    p1_paths: List[Path]
    p2_paths: List[Path]


# NEW: Priority-based data models for new report format
@dataclass
class PriorityPath:
    """Represents a single path in priority-based structure."""
    priority_level: str  # 'P0', 'P1', 'P2', 'P3'
    path_index: int      # 1-indexed (P0.1, P0.2, etc.)
    segments: List[PathSegment]
    length: int
    raw_tuples: List[tuple]  # Original [(src, tgt, action), ...] format
    signature: List[str]      # From path_data['signature']


@dataclass
class PriorityPathCollection:
    """Container for all priority-based paths."""
    p0_paths: List[PriorityPath]
    p1_paths: List[PriorityPath]
    p2_paths: List[PriorityPath]
    p3_paths: List[PriorityPath]
    skipped_edges: List[tuple]
    skipped_loops: List[tuple]
    stats: Dict[str, int]  # {'p0_count': int, 'p1_count': int, 'p2_count': int, 'p3_count': int}


@dataclass
class PathElement:
    """Represents a single element in a path (either a state or an action)."""
    text: str
    tag: Optional[str] = None  # Full tag text for tooltip
    tag_type: Optional[str] = None  # 'NEW', 'LOOP', 'MODIFIED', 'ACTION_CHANGED'
    element_type: Literal["state", "action"] = "state"


class ReportParser:
    def __init__(self, report_path):
        self.report_path = report_path
        self.report_text = ""

    def parse(self) -> List[Cluster]:
        """Parse clustered flow report into structured data."""
        with open(self.report_path, 'r') as f:
            self.report_text = f.read()

        clusters = []

        # Split by P0 archetypes
        archetype_blocks = re.split(r'--- \[P0\] ARCHETYPE #(\d+)', self.report_text)[1:]

        for i in range(0, len(archetype_blocks), 2):
            archetype_num = int(archetype_blocks[i])
            block_content = archetype_blocks[i + 1]

            cluster = self._parse_cluster_block(archetype_num, block_content)
            clusters.append(cluster)

        return clusters

    def _parse_cluster_block(self, archetype_num, block_content):
        """Parse a single cluster block."""
        # Extract P0 path
        p0_match = re.search(r'\(Length: (\d+)\) ---\n(.*?)(?=>>>|\-{80}|$)', block_content, re.DOTALL)
        p0_length = int(p0_match.group(1)) if p0_match else 0
        p0_text = p0_match.group(2).strip() if p0_match else ""
        p0_segments = self._parse_path_segments(p0_text)
        p0_path = Path(path_id=f"P0-{archetype_num}", segments=p0_segments, length=p0_length)

        # Extract P1 paths
        p1_paths = []
        p1_section = re.search(r'>>> \[P1\] Major Variations.*?\n(.*?)(?=>>>|\-{80}|$)', block_content, re.DOTALL)
        if p1_section:
            p1_matches = re.findall(r'P1\.(\d+): (.*?)(?=P1\.\d+:|>>>|$)', p1_section.group(1), re.DOTALL)
            for p1_num, p1_text in p1_matches:
                segments = self._parse_path_segments(p1_text.strip())
                p1_paths.append(Path(path_id=f"P1-{archetype_num}.{p1_num}", segments=segments, length=len(segments)))

        # Extract P2 paths
        p2_paths = []
        p2_section = re.search(r'>>> \[P2\] Minor Differences.*?\n(.*?)(?=\-{80}|$)', block_content, re.DOTALL)
        if p2_section:
            p2_matches = re.findall(r'P2\.(\d+): (.*?)(?=P2\.\d+:|$)', p2_section.group(1), re.DOTALL)
            for p2_num, p2_text in p2_matches:
                segments = self._parse_path_segments(p2_text.strip())
                p2_paths.append(Path(path_id=f"P2-{archetype_num}.{p2_num}", segments=segments, length=len(segments)))

        return Cluster(archetype_id=archetype_num, p0_path=p0_path, p1_paths=p1_paths, p2_paths=p2_paths)

    def _parse_path_segments(self, path_text):
        """Parse path text into segments with tags."""
        segments = []

        # Normalize multi-line paths - collapse line breaks and indentation
        normalized_text = re.sub(r'\n\s+', ' ', path_text.strip())

        if not normalized_text or '(' not in normalized_text:
            return segments

        # Extract the starting state
        start_match = re.match(r'\((\w+)\)', normalized_text)
        if not start_match:
            return segments

        current_state = start_match.group(1)

        # Find all transitions: --[ACTION]--> (TARGET_STATE)
        # Simplified pattern without tag capture groups
        transition_pattern = r'--\s*\[([^\]]+)\]\s*-->\s*\((\w+)\)'
        transitions = re.findall(transition_pattern, normalized_text)

        # Build segments by pairing current_state with each transition
        for action, target in transitions:
            segments.append(PathSegment(
                source=current_state,
                target=target,
                action=action,
                tag=None,  # Always None now
                tag_type=None  # Always None now
            ))

            # Move to next state
            current_state = target

        return segments


def extract_path_elements(segments: List[PathSegment]) -> List[PathElement]:
    """
    Convert path segments into a flat list of alternating states and actions.

    Example:
        Input: [PathSegment(source="STATE_A", action="USER_GREET", target="STATE_B", tag=None)]
        Output: [
            PathElement(text="STATE_A", element_type="state"),
            PathElement(text="USER_GREET", element_type="action"),
            PathElement(text="STATE_B", element_type="state")
        ]
    """
    elements = []

    if not segments:
        return elements

    # Add initial state
    elements.append(PathElement(
        text=segments[0].source,
        element_type="state"
    ))

    # Add action + target state for each segment
    for seg in segments:
        # Action element (no tags)
        elements.append(PathElement(
            text=seg.action,
            tag=None,
            tag_type=None,
            element_type="action"
        ))

        # Target state element (no tag)
        elements.append(PathElement(
            text=seg.target,
            element_type="state"
        ))

    return elements


class PriorityReportParser:
    """Parser for new priority-based text report format."""

    def __init__(self, report_path):
        self.report_path = report_path
        self.report_text = ""

    def parse(self) -> PriorityPathCollection:
        """Parse priority-based report into structured data."""
        with open(self.report_path, 'r') as f:
            self.report_text = f.read()

        # Extract stats from header
        stats = self._parse_stats()

        # Parse each priority section
        p0_paths = self._parse_priority_section('P0', r'=== \[P0\] GOLDEN PATHS.*?===', r'P0\.(\d+) \(Length: (\d+)\):\s*(.*?)(?=P0\.\d+|===|$)')
        p1_paths = self._parse_priority_section('P1', r'=== \[P1\] REQUIRED VARIATIONS.*?===', r'P1\.(\d+) \(Length: (\d+)\):\s*(.*?)(?=P1\.\d+|===|$)')
        p2_paths = self._parse_priority_section('P2', r'=== \[P2\] LOOP STRESS TESTS.*?===', r'P2\.(\d+) \(Length: (\d+)\):\s*(.*?)(?=P2\.\d+|===|$)')
        p3_paths = self._parse_priority_section('P3', r'=== \[P3\] REDUNDANT PATHS.*?===', r'P3\.(\d+) \(Length: (\d+)\):\s*(.*?)(?=P3\.\d+|===|$)')

        # Parse skipped edges/loops
        skipped_edges, skipped_loops = self._parse_skipped()

        return PriorityPathCollection(
            p0_paths=p0_paths,
            p1_paths=p1_paths,
            p2_paths=p2_paths,
            p3_paths=p3_paths,
            skipped_edges=skipped_edges,
            skipped_loops=skipped_loops,
            stats=stats
        )

    def _parse_stats(self) -> Dict[str, int]:
        """Extract stats from report header."""
        stats_pattern = r'P0=(\d+) \| P1=(\d+) \| P2=(\d+) \| P3=(\d+)'
        match = re.search(stats_pattern, self.report_text)

        if match:
            return {
                'p0_count': int(match.group(1)),
                'p1_count': int(match.group(2)),
                'p2_count': int(match.group(3)),
                'p3_count': int(match.group(4))
            }
        return {'p0_count': 0, 'p1_count': 0, 'p2_count': 0, 'p3_count': 0}

    def _parse_priority_section(self, priority_level: str, section_pattern: str, path_pattern: str) -> List[PriorityPath]:
        """Parse a single priority section (P0, P1, P2, or P3)."""
        paths = []

        # Find the section
        section_match = re.search(section_pattern, self.report_text, re.DOTALL)
        if not section_match:
            return paths

        # Extract all paths in this section
        section_text = self.report_text[section_match.end():]

        # Find paths using pattern
        path_matches = re.finditer(path_pattern, section_text, re.DOTALL)

        for match in path_matches:
            path_index = int(match.group(1))
            length = int(match.group(2))
            path_text = match.group(3).strip()

            # Parse path segments using existing helper
            segments = self._parse_path_segments(path_text)

            # Convert segments to raw tuples
            raw_tuples = [(seg.source, seg.target, seg.action) for seg in segments]

            # Create signature (placeholder - not used in display but kept for compatibility)
            signature = []

            priority_path = PriorityPath(
                priority_level=priority_level,
                path_index=path_index,
                segments=segments,
                length=length,
                raw_tuples=raw_tuples,
                signature=signature
            )
            paths.append(priority_path)

        return paths

    def _parse_path_segments(self, path_text: str) -> List[PathSegment]:
        """Parse path text into segments (reuse logic from ReportParser)."""
        segments = []

        # Normalize multi-line paths
        normalized_text = re.sub(r'\n\s+', ' ', path_text.strip())

        if not normalized_text or '(' not in normalized_text:
            return segments

        # Extract starting state
        start_match = re.match(r'\((\w+)\)', normalized_text)
        if not start_match:
            return segments

        current_state = start_match.group(1)

        # Find all transitions: --[ACTION]--> (TARGET_STATE)
        transition_pattern = r'--\s*\[([^\]]+)\]\s*-->\s*\((\w+)\)'
        transitions = re.findall(transition_pattern, normalized_text)

        # Build segments
        for action, target in transitions:
            segments.append(PathSegment(
                source=current_state,
                target=target,
                action=action,
                tag=None,
                tag_type=None
            ))
            current_state = target

        return segments

    def _parse_skipped(self) -> tuple:
        """Parse skipped edges and loops from warning section."""
        skipped_edges = []
        skipped_loops = []

        # Look for WARNING section
        warning_match = re.search(r'WARNING: SKIPPED LOGIC.*?$', self.report_text, re.DOTALL | re.MULTILINE)
        if not warning_match:
            return (skipped_edges, skipped_loops)

        warning_text = warning_match.group(0)

        # Parse skipped edges (simple string representation for now)
        if 'Skipped Edges:' in warning_text:
            # Extract edges list (format: [('src', 'tgt', 'action'), ...])
            # For now, return empty list - can be enhanced if needed
            pass

        if 'Skipped Loops:' in warning_text:
            # Extract loops list
            pass

        return (skipped_edges, skipped_loops)
