import networkx as nx
import re
import difflib

# --- 1. PARSING LOGIC ---
def parse_dot_file(filename):
    edges = []
    # Regex breakdown:
    # 1. (\w+)       -> Captures the Source Node (alphanumeric + underscore)
    # 2. \s*->\s* -> Matches the arrow "->" with optional spaces
    # 3. (\w+)       -> Captures the Target Node
    # 4. (?: ... )?  -> Non-capturing group for the optional label part
    # 5. label="?    -> Matches 'label=' and an optional quote
    # 6. ([^"\]]+)   -> Captures the label text (until a quote or closing bracket)
    edge_pattern = re.compile(r'(\w+)\s*->\s*(\w+)(?:.*label="?([^"\]]+)"?)?')

    try:
        with open(filename, 'r') as f:
            for line in f:
                match = edge_pattern.search(line)
                if match:
                    source = match.group(1)
                    target = match.group(2)
                    # If label is present, use it; otherwise default to AUTO_PROCEED
                    label = match.group(3) if match.group(3) else "AUTO_PROCEED"
                    edges.append((source, target, label))
    except FileNotFoundError:
        print(f"Error: Could not find file '{filename}'")
        return []
    
    return edges

# --- 2. PATH FINDING LOGIC ---
def find_paths_with_one_loop(graph, current_node, end_node, path, visited_counts):
    # Base case: reached the end
    if current_node == end_node:
        yield path
        return

    # Safety check: If node is a dead end (no neighbors), stop here
    if not graph.has_node(current_node) or not list(graph.neighbors(current_node)):
        return

    for neighbor in graph.neighbors(current_node):
        count = visited_counts.get(neighbor, 0)
        
        # Constraint: Allow max 2 visits to handle single loops
        if count < 2:
            visited_counts[neighbor] = count + 1
            
            # Iterate through all edges (actions) between these nodes
            for key in graph[current_node][neighbor]:
                edge_data = graph[current_node][neighbor][key]
                new_segment = (current_node, neighbor, edge_data['action'])
                yield from find_paths_with_one_loop(
                    graph, neighbor, end_node, path + [new_segment], visited_counts.copy()
                )

# --- 3. CLUSTERING & SMART DIFF OUTPUT ---

# CONFIGURATION
STEPS_PER_LINE = 3
THRESHOLD_P2_IDENTICAL = 0.95 # score needs to be 95% or more for it to be categorized as P2
THRESHOLD_P1_VARIATION = 0.7  # score needs to be less than 70% or less for it be P0. Between 70% and 95% becomes P1

# Default start/end nodes (can be overridden in generate_path_analysis)
_START_NODE = "STATE_GREETING"
_END_NODE = "STATE_END_CONVERSATION"

# --- HELPER: FORMAT PATHS ---
def format_diff_path(p1_tuples, p0_tuples=None):
    """
    Simple path formatter without diff tags.
    The p0_tuples parameter is kept for backward compatibility but is ignored.
    """
    # Format the path without any comparison or tags
    path_str = f"({p1_tuples[0][0]})"  # Starting state
    for i, (src, tgt, action) in enumerate(p1_tuples):
        path_str += f" --[{action}]--> ({tgt})"
        # Line break every 3 steps
        if (i + 1) % STEPS_PER_LINE == 0 and (i + 1) < len(p1_tuples):
            path_str += "\n        "
    return path_str

def get_path_signature(path_tuples, start_node=None, end_node=None):
    """Signature for clustering (removes Start/End, collapses loops)"""
    if start_node is None:
        start_node = _START_NODE
    if end_node is None:
        end_node = _END_NODE

    raw_nodes = [path_tuples[0][0]] + [t[1] for t in path_tuples]
    filtered_nodes = [n for n in raw_nodes if n not in (start_node, end_node)]
    if not filtered_nodes: return []
    collapsed = [filtered_nodes[0]]
    for node in filtered_nodes[1:]:
        if node != collapsed[-1]:
            collapsed.append(node)
    return collapsed

def cluster_paths(all_paths, start_node=None, end_node=None):
    """Cluster paths by similarity"""
    # Sort by length for clean P0s
    path_data = []
    for p in all_paths:
        path_data.append({
            'raw': p,
            'signature': get_path_signature(p, start_node, end_node),
            'length': len(p)
        })
    path_data.sort(key=lambda x: x['length'])

    clusters = []

    for current in path_data:
        assigned = False
        for cluster in clusters:
            p0_sig = cluster['p0']['signature']
            curr_sig = current['signature']

            matcher = difflib.SequenceMatcher(None, p0_sig, curr_sig)
            score = matcher.ratio()

            if score >= THRESHOLD_P2_IDENTICAL:
                cluster['p2'].append(current)
                assigned = True
                break
            elif score >= THRESHOLD_P1_VARIATION:
                cluster['p1'].append(current)
                assigned = True
                break

        if not assigned:
            clusters.append({'p0': current, 'p1': [], 'p2': []})

    return clusters

def generate_path_analysis(dot_source_path, output_report_path='clustered_flow_report.txt',
                          start_node='STATE_GREETING', end_node='STATE_END_CONVERSATION'):
    """
    Analyze conversation paths from flowchart DOT source.

    Args:
        dot_source_path: Path to DOT source file
        output_report_path: Where to save the analysis report
        start_node: Starting state
        end_node: Terminal state

    Returns:
        str: Path to generated report
    """
    parsed_edges = parse_dot_file(dot_source_path)

    G = nx.MultiDiGraph()
    for u, v, label in parsed_edges:
        G.add_edge(u, v, action=label)

    if not G.has_node(start_node) or not G.has_node(end_node):
        raise ValueError(f"Start '{start_node}' or End '{end_node}' not found in graph.")

    raw_paths = list(find_paths_with_one_loop(G, start_node, end_node, [], {start_node: 1}))
    final_clusters = cluster_paths(raw_paths, start_node, end_node)

    # Write report
    with open(output_report_path, "w") as f:
        f.write(f"CLUSTERING REPORT\n")
        f.write(f"Total Paths: {len(raw_paths)} | Unique Archetypes (P0): {len(final_clusters)}\n")
        f.write("="*80 + "\n\n")

        for i, cluster in enumerate(final_clusters, 1):
            p0 = cluster['p0']
            p0_raw = p0['raw']

            f.write(f"--- [P0] ARCHETYPE #{i} (Length: {p0['length']}) ---\n")
            f.write(f"{format_diff_path(p0_raw, None)}\n\n")

            if cluster['p1']:
                f.write(f"   >>> [P1] Major Variations ({len(cluster['p1'])} paths)\n")
                for j, p1 in enumerate(cluster['p1'], 1):
                    formatted_p1 = format_diff_path(p1['raw'], p0_raw)
                    f.write(f"   P1.{j}: {formatted_p1}\n\n")

            if cluster['p2']:
                f.write(f"   >>> [P2] Minor Differences / Loops ({len(cluster['p2'])} paths)\n")
                for k, p2 in enumerate(cluster['p2'], 1):
                    formatted_p2 = format_diff_path(p2['raw'], p0_raw)
                    f.write(f"   P2.{k}: {formatted_p2}\n\n")

            f.write("-" * 80 + "\n\n")

    return output_report_path


if __name__ == "__main__":
    # CLI execution - existing behavior preserved
    input_filename = "flowchart_collections_std"
    output_filename = "clustered_flow_report.txt"

    start_node = "STATE_GREETING"
    end_node = "STATE_END_CONVERSATION"

    # Build graph from DOT file
    parsed_edges = parse_dot_file(input_filename)
    G = nx.MultiDiGraph()
    for u, v, label in parsed_edges:
        G.add_edge(u, v, action=label)

    print(f"Successfully loaded {len(parsed_edges)} edges from {input_filename}")

    if not G.has_node(start_node) or not G.has_node(end_node):
        print(f"Error: Start '{start_node}' or End '{end_node}' not found.")
        exit(1)

    print("Finding paths...")
    try:
        report_path = generate_path_analysis(input_filename, output_filename, start_node, end_node)
        print(f"Done! Clustered report saved to: {report_path}")
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

