# Code that uses the transitions json from the LLM to convert it into a flowchart
import graphviz
import json


def generate_flowchart(json_data, output_base_name='flowchart_claude'):
    """
    Generate flowchart from FSM JSON data.

    Args:
        json_data: Dict with 'workflow_logic.transitions' structure
        output_base_name: Base name for output files (no extension)

    Returns:
        tuple: (png_path, dot_source_path)
    """
    try:
        transitions = json_data['workflow_logic']['transitions']
    except KeyError:
        raise ValueError("JSON structure mismatch. Could not find 'workflow_logic' or 'transitions'.")

    # Filter valid transitions (all required fields must be non-null)
    valid_transitions = [
        t for t in transitions
        if t.get('from_state') and t.get('to_state') and t.get('trigger_intent')
    ]

    # Log skipped transitions for debugging
    skipped_count = len(transitions) - len(valid_transitions)
    if skipped_count > 0:
        print(f"Note: Skipped {skipped_count} transition(s) with missing/null fields (likely terminal states)")

    dot = graphviz.Digraph(comment='Voice Agent Flow', format='png')
    dot.attr(rankdir='TB')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#E3F2FD')

    for item in valid_transitions:
        dot.edge(item['from_state'], item['to_state'], label=item['trigger_intent'])

    png_path = dot.render(output_base_name, view=False)
    dot_source_path = output_base_name  # Graphviz creates this

    return png_path, dot_source_path


if __name__ == "__main__":
    # CLI execution - existing behavior preserved
    filename = 'LLM_output_axis.json'

    try:
        with open(filename, 'r') as f:
            master_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find '{filename}'. Check the file name!")
        exit()

    print(f"Successfully loaded {len(master_data['workflow_logic']['transitions'])} transitions.")

    png_path, dot_path = generate_flowchart(master_data, 'flowchart_claude')
    print(f"Flowchart saved at: {png_path}")