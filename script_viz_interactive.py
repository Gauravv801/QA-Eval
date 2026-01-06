# script_viz_interactive.py
import json
import os
import networkx as nx
from pyvis.network import Network
import sys
try:
    # Attempt to import pygraphviz (preferred)
    from networkx.drawing.nx_agraph import graphviz_layout
except ImportError:
    try:
        # Fallback to pydot
        from networkx.drawing.nx_pydot import graphviz_layout
    except ImportError:
        # Fallback if neither is installed
        graphviz_layout = None

# ---------------- CONFIGURATION ---------------- #
INPUT_FILE = "output.json"
OUTPUT_FILE = "flowchart_interactive.html"
MAX_LABEL_LENGTH = 20  # Max chars for edge label before truncation

# Node Styles
COLOR_START = "#4CAF50"  # Green
COLOR_END = "#F44336"    # Red
COLOR_DEFAULT = "#E3F2FD" # Light Blue
COLOR_BORDER = "#1565C0"  # Dark Blue Border

def truncate_label(text, length=20):
    """
    Truncates text to 'length' and adds ellipsis if longer.
    Returns (truncated_text, original_text)
    """
    if not text:
        return "", ""
    
    text = str(text).strip()
    if len(text) <= length:
        return text, text
    else:
        return text[:length] + "...", text

def generate_interactive_graph(json_data=None, output_path=None):
    """
    Generate interactive HTML visualization from FSM JSON data.

    Args:
        json_data (dict): FSM data structure with workflow_logic.transitions
        output_path (str): Path where HTML file should be saved

    Returns:
        str: Absolute path to generated HTML file
    """
    # Use defaults for CLI usage
    if json_data is None:
        print(f"--- STARTING INTERACTIVE VISUALIZATION ---")

        # 1. Validation & Loading
        if not os.path.exists(INPUT_FILE):
            print(f"Error: {INPUT_FILE} not found. Run Script 1 first.")
            sys.exit(1)

        try:
            with open(INPUT_FILE, 'r') as f:
                json_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Failed to parse {INPUT_FILE}. Invalid JSON.")
            sys.exit(1)

    if output_path is None:
        output_path = OUTPUT_FILE

    transitions = json_data.get("workflow_logic", {}).get("transitions", [])
    if not transitions:
        print("Warning: No transitions found in JSON.")
        sys.exit(0)

    # 2. Build NetworkX Graph
    G = nx.MultiDiGraph()  # Use MultiDiGraph to support parallel edges (multiple transitions between same states)

    print(f"Processing {len(transitions)} transitions...")
    
    # --- START OF CHANGED SECTION ---
    
    # Track how many connections exist between specific pairs to offset them
    edge_counts = {}

    for t in transitions:
        src = t.get("from_state")
        dst = t.get("to_state")
        trigger = t.get("trigger_intent")

        # Skip invalid transitions
        if not src or not dst:
            continue
            
        # Clean state names
        src = src.strip()
        dst = dst.strip()

        # Handle Label Truncation & Tooltip
        label_display, full_text = truncate_label(trigger, MAX_LABEL_LENGTH)

        # --- LOGIC TO FIX OVERLAPPING EDGES ---
        # 1. Generate a unique key for this source-destination pair
        pair_key = (src, dst)
        
        # 2. Increment the count for this pair
        current_count = edge_counts.get(pair_key, 0)
        edge_counts[pair_key] = current_count + 1
        
        # 3. Calculate a unique curve "roundness" based on the count
        # The first edge gets 0.1, the second 0.25, the third 0.4, etc.
        # This forces them to draw distinct arcs.
        roundness_val = 0.1 + (current_count * 0.15)

        # 4. Add Edge with the specific 'smooth' setting injected directly
        G.add_edge(
            src, 
            dst, 
            label=label_display, 
            title=f"Intent: {full_text}",
            smooth={'type': 'curvedCW', 'roundness': roundness_val}
        )
    # --- END OF CHANGED SECTION ---
    
    print("Calculating tree layout...")
    if graphviz_layout:
        # 'dot' is the specific Graphviz engine for hierarchical trees
        # args='-Grankdir=UD' ensures Up-Down direction
        pos = graphviz_layout(G, prog='dot')
    else:
        print("Warning: PyGraphviz/PyDot not found. Falling back to spring layout.")
        pos = nx.spring_layout(G, seed=42)

    # Assign coordinates to nodes so PyVis respects them.
    # We multiply by a scale factor to spread them out on the HTML canvas.
    SCALE_FACTOR = 1.5
    for node, coords in pos.items():
        # PyVis expects x, y attributes. 
        # Note: Graphviz (0,0) is bottom-left, HTML is top-left.
        # We invert Y (-coords[1]) to keep the visual hierarchy Up-to-Down.
        G.nodes[node]['x'] = coords[0] * SCALE_FACTOR
        G.nodes[node]['y'] = -coords[1] * SCALE_FACTOR

    # 3. Configure PyVis Network
    # directed=True gives us arrows
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    
    # Load data from NetworkX
    net.from_nx(G)

    # 4. Apply Visual Styling to Nodes
    for node in net.nodes:
        node_id = node['id']
        
        # Base Style
        node['shape'] = 'box'
        node['borderWidth'] = 2
        node['color'] = {
            'background': COLOR_DEFAULT,
            'border': COLOR_BORDER,
            'highlight': {
                'background': '#BBDEFB',
                'border': '#0D47A1'
            }
        }
        node['font'] = {'size': 16, 'face': 'arial'}
        node['margin'] = 10

        # Special colors for Start/End
        if "GREETING" in node_id.upper() or "START" in node_id.upper():
             node['color']['background'] = COLOR_START
             node['color']['border'] = "#2E7D32"
             node['font']['color'] = "white"
        
        if "END" in node_id.upper():
             node['color']['background'] = COLOR_END
             node['color']['border'] = "#C62828"
             node['font']['color'] = "white"

    # 5. Advanced Physics & Layout Configuration
    # We inject a specific set of options to get:
    # - Top-Down hierarchy (Hierarchical Layout)
    # - Drag capability (Hierarchical Repulsion)
    # - Smooth curves
    
    options = {
        "layout": {
            "hierarchical": {
                "enabled": False
            }
        },
        "physics": {
            "enabled": False,
            "stabilization": False
            },
        "edges": {
            "smooth": {
                "type": "curvedCW",  # Automatically curves parallel edges differently to avoid overlap
                "roundness": 0.2
            },
            "color": {"color": "#666666", "highlight": "#000000"},
            "font": {"size": 12, "align": "middle", "background": "white"}
        },
        "interaction": {
            "dragNodes": True,
            "hover": True,
            "navigationButtons": True,
            "zoomView": True
        }
    }

    # Inject options as JSON string
    net.set_options(json.dumps(options))

    # 6. Save Output
    try:
        net.save_graph(output_path)
        print(f"Success! Interactive chart saved to: {output_path}")
        print(f"Stats: {G.number_of_nodes()} states, {G.number_of_edges()} transitions")
    except Exception as e:
        print(f"Error saving HTML: {e}")
        raise e   #Re-raise to alert the calling function
    
    return os.path.abspath(output_path)

if __name__ == "__main__":
    generate_interactive_graph()