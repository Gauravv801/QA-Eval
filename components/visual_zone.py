import streamlit as st

def render_visual_zone(png_path, dot_path):
    """Display flowchart with download buttons."""
    st.subheader("FSM Flowchart Visualization")

    # Display flowchart
    st.image(png_path, use_container_width=True)

    # Download buttons
    col1, col2 = st.columns(2)

    with col1:
        with open(png_path, 'rb') as f:
            st.download_button(
                "Download PNG Image",
                f.read(),
                file_name="flowchart.png",
                mime="image/png"
            )

    with col2:
        with open(dot_path, 'r') as f:
            st.download_button(
                "Download DOT Source",
                f.read(),
                file_name="flowchart.dot",
                mime="text/plain"
            )
