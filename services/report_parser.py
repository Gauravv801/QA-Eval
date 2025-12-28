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
