import streamlit as st
import os


def render_results_zone(clusters, report_path):
    """Render hierarchical path display with basic Streamlit components."""
    st.subheader("Conversation Path Analysis")

    # Display Excel generation error if present
    if st.session_state.excel_error:
        st.warning(
            f"**Excel export failed**: {st.session_state.excel_error}\n\n"
            "The text report is available, but the Excel (.xlsx) download is unavailable."
        )

    # Statistics row with standard metrics
    total_paths = sum(1 + len(c.p1_paths) + len(c.p2_paths) for c in clusters)
    total_archetypes = len(clusters)
    total_p1 = sum(len(c.p1_paths) for c in clusters)
    total_p2 = sum(len(c.p2_paths) for c in clusters)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Paths", total_paths)

    with col2:
        st.metric("Archetypes (P0)", total_archetypes)

    with col3:
        st.metric("Major Variations (P1)", total_p1)

    with col4:
        st.metric("Minor Differences (P2)", total_p2)

    # Download buttons
    col1, col2 = st.columns(2)

    with col1:
        with open(report_path, 'r') as f:
            st.download_button(
                "Download TXT Report",
                f.read(),
                file_name="clustered_flow_report.txt",
                mime="text/plain"
            )

    with col2:
        if st.session_state.excel_report_path and os.path.exists(st.session_state.excel_report_path):
            with open(st.session_state.excel_report_path, 'rb') as f:
                st.download_button(
                    "Download XLSX Report",
                    f.read(),
                    file_name="clustered_flow_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.button(
                "Download XLSX Report",
                disabled=True,
                help="Excel export not available"
            )

    st.markdown("---")

    # Render clusters
    for cluster in clusters:
        with st.expander(
            f"ARCHETYPE #{cluster.archetype_id}  |  Length: {cluster.p0_path.length} steps",
            expanded=False
        ):
            # P0 section
            st.markdown("**Base Path (P0)**")
            st.text(render_path_text(cluster.p0_path.segments))

            # P1 section
            if cluster.p1_paths:
                st.markdown(f"**Major Variations (P1) — {len(cluster.p1_paths)} paths**")
                for path in cluster.p1_paths:
                    with st.expander(f"{path.path_id}", expanded=False):
                        st.text(render_path_text(path.segments))

            # P2 section
            if cluster.p2_paths:
                st.markdown(f"**Minor Differences (P2) — {len(cluster.p2_paths)} paths**")
                for path in cluster.p2_paths:
                    with st.expander(f"{path.path_id}", expanded=False):
                        st.text(render_path_text(path.segments))


def render_path_text(segments):
    """Render path segments as plain text."""
    parts = []

    if segments:
        parts.append(f"({segments[0].source})")

    for seg in segments:
        parts.append(f" --[{seg.action}]--> ({seg.target})")

    return "".join(parts)
