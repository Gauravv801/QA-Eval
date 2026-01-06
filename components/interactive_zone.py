import streamlit as st
import streamlit.components.v1 as components


def render_interactive_zone(html_path):
    """Display interactive flowchart with iframe and download button."""
    st.subheader("Interactive FSM Flowchart")

    if not html_path:
        st.info("Interactive visualization not available for this run.")
        return

    # Initialize content variable (shared by iframe and download)
    html_content = None

    # Embed iframe
    try:
        # Check if URL (historical) or local file (active)
        if html_path.startswith('http'):
            import requests
            response = requests.get(html_path)
            html_content = response.text
        else:
            with open(html_path, 'r') as f:
                html_content = f.read()

        # Render interactive graph
        components.html(html_content, height=800, scrolling=True)

    except Exception as e:
        st.error(f"Failed to load interactive visualization: {e}")

    st.markdown("---")

    # Download button (reuses fetched content)
    if html_content:
        st.download_button(
            "Download Interactive HTML",
            html_content,
            file_name="flowchart_interactive.html",
            mime="text/html"
        )
    else:
        st.warning("Download unavailable: content not loaded")
