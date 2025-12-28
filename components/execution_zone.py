import streamlit as st

def render_thinking_console(thinking_text, container_id=None, token_count=None):
    """
    Display thinking process in basic expander.

    Args:
        thinking_text: Raw thinking output from Claude
        container_id: Optional unique container ID (not used in simplified version)
        token_count: Optional token count for display
    """
    # Calculate rough token count if not provided
    if token_count is None:
        token_count = len(thinking_text.split())

    # Display in basic expander
    with st.expander(f"Extended Thinking Output ({token_count:,} tokens)", expanded=True):
        st.text(thinking_text)
