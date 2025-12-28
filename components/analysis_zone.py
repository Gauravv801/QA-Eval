import streamlit as st

def render_analysis_zone(cost_metrics, output_json):
    """Display cost metrics and JSON output."""
    st.subheader("API Request Summary")

    # Standard metric cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Input Tokens", f"{cost_metrics['input_tokens']:,}")

    with col2:
        st.metric("Output Tokens", f"{cost_metrics['output_tokens']:,}")

    with col3:
        st.metric("Total Cost", f"${cost_metrics['total_cost_usd']:.4f}")

    with col4:
        st.metric("Model", cost_metrics['model'])

    # JSON Viewer
    with st.expander("View Raw FSM JSON"):
        st.json(output_json)
