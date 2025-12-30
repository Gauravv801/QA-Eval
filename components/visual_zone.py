import streamlit as st

def render_visual_zone(png_path, dot_path):
    """Display flowchart with download buttons."""
    st.subheader("FSM Flowchart Visualization")

    # Display flowchart (handle both URLs and local paths)
    if png_path:
        st.image(png_path, use_container_width=True)

    # Download buttons
    col1, col2 = st.columns(2)

    with col1:
        # Check if PNG is a URL (historical run from Supabase) or local file
        if png_path and png_path.startswith('http'):
            # Historical run - direct link to Supabase Storage
            st.markdown(f"[Download PNG Image]({png_path})")
        elif png_path:
            # Active run - local file download
            with open(png_path, 'rb') as f:
                st.download_button(
                    "Download PNG Image",
                    f.read(),
                    file_name="flowchart.png",
                    mime="image/png"
                )

    with col2:
        # DOT source is always text content (not a URL)
        if isinstance(dot_path, str) and not dot_path.startswith('http'):
            # Check if it's a file path
            try:
                with open(dot_path, 'r') as f:
                    dot_content = f.read()
            except (FileNotFoundError, OSError):
                # It's already text content (from database)
                dot_content = dot_path
        else:
            dot_content = dot_path

        st.download_button(
            "Download DOT Source",
            dot_content,
            file_name="flowchart.dot",
            mime="text/plain"
        )
