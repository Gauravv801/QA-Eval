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
    """Cluster paths by similarity using Best-Fit logic"""
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
        best_cluster = None
        best_score = -1.0
        
        # PASS 1: Check ALL existing clusters to find the highest score
        for cluster in clusters:
            p0_sig = cluster['p0']['signature']
            curr_sig = current['signature']

            matcher = difflib.SequenceMatcher(None, p0_sig, curr_sig)
            score = matcher.ratio()

            # Keep track of the winner (highest score found so far)
            if score > best_score:
                best_score = score
                best_cluster = cluster

        # PASS 2: Assign to the best winner found (if it meets thresholds)
        if best_cluster and best_score >= THRESHOLD_P2_IDENTICAL:
            best_cluster['p2'].append(current)
        elif best_cluster and best_score >= THRESHOLD_P1_VARIATION:
            best_cluster['p1'].append(current)
        else:
            # If no existing cluster was close enough, create a new one
            clusters.append({'p0': current, 'p1': [], 'p2': []})

    return clusters


# --- 4. PRIORITIZATION LOGIC (NEW) ---

def prioritize_paths(final_clusters):
    """
    Phase 0: Setup - Prepare data structures for prioritization.
    Goal: Reduce combinatorial explosion by filtering P1/P2 based on edge coverage.
    """
    # --- 1. Construct ALL_EDGES (The Universe of Obligation) ---
    all_edges = set()
    
    # Helper to harvest edges from a list of path dictionaries
    def _harvest_edges(path_dicts):
        for p_data in path_dicts:
            for edge in p_data['raw']:
                # Ensure format is strictly (from_state, to_state, action)
                all_edges.add(edge)

    # --- 2. Construct CANDIDATE_POOL & Extract P0s ---
    p0_paths = []     # The "Sacrosanct" list
    candidate_pool = [] # The merged pool to filter (P1 + P2)

    for cluster in final_clusters:
        # P0 is a single dict object
        p0_paths.append(cluster['p0']) 
        
        # P1 and P2 are lists of dict objects
        candidate_pool.extend(cluster['p1'])
        candidate_pool.extend(cluster['p2'])

    # Harvest edges from EVERYONE to build the full universe
    _harvest_edges(p0_paths)
    _harvest_edges(candidate_pool)

    # --- 3. Create Target Sub-sets ---
    target_linear_edges = set()
    target_loops_edges = set()

    for edge in all_edges:
        src, tgt, action = edge
        if src == tgt:
            target_loops_edges.add(edge)
        else:
            target_linear_edges.add(edge)

    # --- 4. Initialize Tracking ---
    covered_edges = set() # Starts empty

    # --- Phase 1: The Golden Path (Final P0) ---
    final_p0 = []
    
    for path_data in p0_paths:
        # Action: Add all P0 paths to FINAL_P0 list
        final_p0.append(path_data)
        
        # Action: Iterate through every step and mark as COVERED
        for edge in path_data['raw']:
            # edge is already (from, to, action)
            covered_edges.add(edge)

    # --- Phase 2: Greedy Discovery (Final P1) ---
    final_p1 = []
    skipped_edges = [] 

    while True:
        # 1. Calculate Uncovered Linear Edges
        uncovered_linear = target_linear_edges - covered_edges
        
        if not uncovered_linear:
            break # Success: All linear logic is covered

        # SAFETY CHECK: If we run out of candidates but still have uncovered edges
        if not candidate_pool:
            skipped_edges.extend(list(uncovered_linear))
            break
            
        best_candidate = None
        best_score = 0
        best_idx = -1
        
        # 2. Score Candidates
        for i, candidate in enumerate(candidate_pool):
            # Score = Count of unique edges in this path that exist in UNCOVERED_LINEAR
            path_edges = set(candidate['raw'])
            score = len(path_edges.intersection(uncovered_linear))
            
            if score > best_score:
                best_score = score
                best_candidate = candidate
                best_idx = i
            elif score == best_score and best_score > 0:
                # Tie-Breaker: Shortest path length
                if candidate['length'] < best_candidate['length']:
                    best_candidate = candidate
                    best_idx = i
        
        # 3. Selection & Termination
        if best_score == 0:
            # Remaining edges cannot be covered by any candidate (should be rare)
            skipped_edges.extend(list(uncovered_linear))
            break
            
        # 4. Update
        # Move path to FINAL_P1
        final_p1.append(best_candidate)
        
        # Add all unique edges to COVERED_EDGES (linear & loops)
        for edge in best_candidate['raw']:
            covered_edges.add(edge)
            
        # Remove from Candidate Pool
        candidate_pool.pop(best_idx)
    
    # --- Phase 3: Loop Stress (Final P2) ---
    final_p2 = []
    skipped_loops = []

    # Iterate until we have tried to cover every loop
    while True:
        # Calculate Uncovered Loops
        uncovered_loops = target_loops_edges - covered_edges
        
        if not uncovered_loops:
            break

        # SAFETY CHECK: If pool is empty
        if not candidate_pool:
            skipped_loops.extend(list(uncovered_loops))
            break

        # Pick one target loop to focus on (order doesn't matter, set is unordered)
        target_loop = next(iter(uncovered_loops))
        
        best_candidate = None
        best_len = float('inf')
        best_idx = -1

        # Scan CANDIDATE_POOL for shortest path containing this specific loop
        for i, candidate in enumerate(candidate_pool):
            path_edges = candidate['raw']
            if target_loop in path_edges:
                if candidate['length'] < best_len:
                    best_len = candidate['length']
                    best_candidate = candidate
                    best_idx = i
        
        # Update
        if best_candidate:
            # Found a path for this loop
            final_p2.append(best_candidate)
            
            # Add all unique edges to COVERED_EDGES
            for edge in best_candidate['raw']:
                covered_edges.add(edge)
            
            # Remove from Candidate Pool
            candidate_pool.pop(best_idx)
        else:
            # No path found in candidate pool covers this loop (orphan loop)
            skipped_loops.append(target_loop)
            # Force remove from calculation to prevent infinite loop
            # (Note: In valid FSMs this shouldn't happen if edge existed in input)
            covered_edges.add(target_loop)

    # --- Phase 4: The Archive (Final P3) ---
    final_p3 = list(candidate_pool) # Everything remaining

    # Return the re-bucketed hierarchy
    return {
        "final_p0": final_p0,
        "final_p1": final_p1,
        "final_p2": final_p2,
        "final_p3": final_p3,
        "skipped_edges": skipped_edges,
        "skipped_loops": skipped_loops,
        "stats": {
            "p0_count": len(final_p0),
            "p1_count": len(final_p1),
            "p2_count": len(final_p2),
            "p3_count": len(final_p3)
        }
    }


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
        tuple: (prioritized_dict, report_path_str)
            - prioritized_dict: Dictionary with keys 'final_p0', 'final_p1', 'final_p2',
                                'final_p3', 'skipped_edges', 'skipped_loops', 'stats'
            - report_path_str: Path to generated text report file
    """
    parsed_edges = parse_dot_file(dot_source_path)

    G = nx.MultiDiGraph()
    for u, v, label in parsed_edges:
        G.add_edge(u, v, action=label)

    if not G.has_node(start_node) or not G.has_node(end_node):
        raise ValueError(f"Start '{start_node}' or End '{end_node}' not found in graph.")

    raw_paths = list(find_paths_with_one_loop(G, start_node, end_node, [], {start_node: 1}))
    final_clusters = cluster_paths(raw_paths, start_node, end_node)

    # # Write report
    # with open(output_report_path, "w") as f:
    #     f.write(f"CLUSTERING REPORT\n")
    #     f.write(f"Total Paths: {len(raw_paths)} | Unique Archetypes (P0): {len(final_clusters)}\n")
    #     f.write("="*80 + "\n\n")

    #     for i, cluster in enumerate(final_clusters, 1):
    #         p0 = cluster['p0']
    #         p0_raw = p0['raw']

    #         f.write(f"--- [P0] ARCHETYPE #{i} (Length: {p0['length']}) ---\n")
    #         f.write(f"{format_diff_path(p0_raw, None)}\n\n")

    #         if cluster['p1']:
    #             f.write(f"   >>> [P1] Major Variations ({len(cluster['p1'])} paths)\n")
    #             for j, p1 in enumerate(cluster['p1'], 1):
    #                 formatted_p1 = format_diff_path(p1['raw'], p0_raw)
    #                 f.write(f"   P1.{j}: {formatted_p1}\n\n")

    #         if cluster['p2']:
    #             f.write(f"   >>> [P2] Minor Differences / Loops ({len(cluster['p2'])} paths)\n")
    #             for k, p2 in enumerate(cluster['p2'], 1):
    #                 formatted_p2 = format_diff_path(p2['raw'], p0_raw)
    #                 f.write(f"   P2.{k}: {formatted_p2}\n\n")

    #         f.write("-" * 80 + "\n\n")

    # 3. Prioritization (Coverage-Based) <--- NEW STEP
    prioritized = prioritize_paths(final_clusters)

    # 4. Write Report (Updated for New Hierarchy)
    with open(output_report_path, "w") as f:
        f.write(f"CLUSTERING REPORT (Prioritized)\n")
        f.write(f"Total Raw Paths: {len(raw_paths)}\n")
        f.write(f"Final Counts: P0={prioritized['stats']['p0_count']} | P1={prioritized['stats']['p1_count']} | ")
        f.write(f"P2={prioritized['stats']['p2_count']} | P3={prioritized['stats']['p3_count']}\n")
        f.write("="*80 + "\n\n")

        # --- SECTION P0: ARCHETYPES ---
        f.write(f"=== [P0] GOLDEN PATHS (Unique Archetypes) ===\n")
        for i, p0 in enumerate(prioritized['final_p0'], 1):
            f.write(f"P0.{i} (Length: {p0['length']}):\n")
            f.write(f"{format_diff_path(p0['raw'])}\n\n")
        f.write("-" * 80 + "\n\n")

        # --- SECTION P1: MAJOR VARIATIONS (Logic Coverage) ---
        f.write(f"=== [P1] REQUIRED VARIATIONS (New Logic Discovery) ===\n")
        if prioritized['final_p1']:
            for i, p1 in enumerate(prioritized['final_p1'], 1):
                f.write(f"P1.{i} (Length: {p1['length']}):\n")
                f.write(f"{format_diff_path(p1['raw'])}\n\n")
        else:
            f.write("No additional logic paths found beyond P0.\n\n")
        f.write("-" * 80 + "\n\n")

        # --- SECTION P2: LOOP STRESS ---
        f.write(f"=== [P2] LOOP STRESS TESTS (Self-Loops) ===\n")
        if prioritized['final_p2']:
            for i, p2 in enumerate(prioritized['final_p2'], 1):
                f.write(f"P2.{i} (Length: {p2['length']}):\n")
                f.write(f"{format_diff_path(p2['raw'])}\n\n")
        else:
            f.write("All loops covered by P0/P1 or none exist.\n\n")
        f.write("-" * 80 + "\n\n")

        # --- SECTION P3: ARCHIVE ---
        f.write(f"=== [P3] REDUNDANT PATHS (Archive) ===\n")
        f.write(f"Total: {len(prioritized['final_p3'])}\n")
        
        # --- SKIPPED REPORT ---
        if prioritized['skipped_edges'] or prioritized['skipped_loops']:
             f.write("\n" + "="*80 + "\n")
             f.write("WARNING: SKIPPED LOGIC (Unreachable/Orphaned)\n")
             if prioritized['skipped_edges']:
                 f.write(f"Skipped Edges: {prioritized['skipped_edges']}\n")
             if prioritized['skipped_loops']:
                 f.write(f"Skipped Loops: {prioritized['skipped_loops']}\n")

    # Return tuple: (prioritized_dict, report_path)
    return (prioritized, output_report_path)

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
        prioritized_dict, report_path = generate_path_analysis(input_filename, output_filename, start_node, end_node)
        print(f"Done! Clustered report saved to: {report_path}")
        print(f"Stats: P0={prioritized_dict['stats']['p0_count']}, P1={prioritized_dict['stats']['p1_count']}, P2={prioritized_dict['stats']['p2_count']}, P3={prioritized_dict['stats']['p3_count']}")
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)