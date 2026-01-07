import streamlit as st
import os


def render_results_zone(clusters, report_path):
    """Render hierarchical path display with basic Streamlit components."""
    # Calculate total paths for header
    total_paths = sum(1 + len(c.p1_paths) + len(c.p2_paths) for c in clusters)
    st.subheader(f"Conversation Path Analysis ({total_paths})")

    # Display Excel generation error if present
    if st.session_state.excel_error:
        st.warning(
            f"**Excel export failed**: {st.session_state.excel_error}\n\n"
            "The text report is available, but the Excel (.xlsx) download is unavailable."
        )
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
        excel_path = st.session_state.excel_report_path
        if excel_path:
            # Check if it's a URL (historical run from Supabase) or local file
            if excel_path.startswith('http'):
                # Historical run - direct link to Supabase Storage
                st.markdown(f"[Download XLSX Report]({excel_path})")
            elif os.path.exists(excel_path):
                # Active run - local file download
                with open(excel_path, 'rb') as f:
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


def render_results_zone_priority(priority_collection, report_path):
    """Render flat priority sections (P0, P1, P2, P3)."""
    # Calculate total paths for header
    stats = priority_collection.stats
    total_paths = stats['p0_count'] + stats['p1_count'] + stats['p2_count'] + stats['p3_count']
    st.subheader(f"Conversation Path Analysis ({total_paths})")

    # Display Excel generation error if present
    if st.session_state.excel_error:
        st.warning(
            f"**Excel export failed**: {st.session_state.excel_error}\n\n"
            "The text report is available, but the Excel (.xlsx) download is unavailable."
        )
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Base Paths (P0)", stats['p0_count'])

    with col2:
        st.metric("Major Variations (P1)", stats['p1_count'])

    with col3:
        st.metric("Loop Tests (P2)", stats['p2_count'])

    with col4:
        st.metric("Supplemental Paths (P3)", stats['p3_count'])

    # Download buttons (reuse same logic as legacy version)
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
        excel_path = st.session_state.excel_report_path
        if excel_path:
            if excel_path.startswith('http'):
                st.markdown(f"[Download XLSX Report]({excel_path})")
            elif os.path.exists(excel_path):
                with open(excel_path, 'rb') as f:
                    st.download_button(
                        "Download XLSX Report",
                        f.read(),
                        file_name="clustered_flow_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.button("Download XLSX Report", disabled=True, help="Excel export not available")
        else:
            st.button("Download XLSX Report", disabled=True, help="Excel export not available")

    st.markdown("---")

    # P0 Section - Base Paths (Archetypes)
    with st.expander(f"P0: Base Paths ({stats['p0_count']} paths)", expanded=True):
        st.markdown("**Core conversation archetypes - highest priority for testing**")
        if stats['p0_count'] == 0:
            st.info("No P0 paths found.")
        else:
            for path in priority_collection.p0_paths:
                with st.expander(f"P0.{path.path_index} (Length: {path.length})", expanded=False):
                    st.text(render_path_text(path.segments))

    # P1 Section - Logic Variations
    with st.expander(f"P1: Logic Variations ({stats['p1_count']} paths)", expanded=False):
        st.markdown("**Required variations that cover new edge logic**")
        if stats['p1_count'] == 0:
            st.info("No additional logic variations found beyond P0 paths.")
        else:
            for path in priority_collection.p1_paths:
                with st.expander(f"P1.{path.path_index} (Length: {path.length})", expanded=False):
                    st.text(render_path_text(path.segments))

    # P2 Section - Loop Stress Tests
    with st.expander(f"P2: Loop Stress Tests ({stats['p2_count']} paths)", expanded=False):
        st.markdown("**Paths that test self-loop transitions**")
        if stats['p2_count'] == 0:
            st.info("All loops covered by P0/P1 or none exist.")
        else:
            for path in priority_collection.p2_paths:
                with st.expander(f"P2.{path.path_index} (Length: {path.length})", expanded=False):
                    st.text(render_path_text(path.segments))

    # P3 Section - Supplemental Paths (Archive)
    with st.expander(f"P3: Supplemental Paths ({stats['p3_count']} paths)", expanded=False):
        st.markdown("**Archive - paths fully covered by P0/P1/P2**")
        if stats['p3_count'] == 0:
            st.success("No supplemental paths - all generated paths are useful!")
        else:
            for path in priority_collection.p3_paths:
                with st.expander(f"P3.{path.path_index} (Length: {path.length})", expanded=False):
                    st.text(render_path_text(path.segments))

    # Warnings section for skipped edges/loops
    if priority_collection.skipped_edges or priority_collection.skipped_loops:
        st.warning("**Unreachable Logic Detected**")
        if priority_collection.skipped_edges:
            with st.expander(f"Skipped Edges ({len(priority_collection.skipped_edges)})", expanded=False):
                if priority_collection.skipped_edges:
                    for edge in priority_collection.skipped_edges:
                        st.code(f"{edge[0]} --[{edge[2]}]--> {edge[1]}")
                else:
                    st.info("No skipped edges.")

        if priority_collection.skipped_loops:
            with st.expander(f"Skipped Loops ({len(priority_collection.skipped_loops)})", expanded=False):
                if priority_collection.skipped_loops:
                    for loop in priority_collection.skipped_loops:
                        st.code(f"{loop[0]} --[{loop[2]}]--> {loop[1]}")
                else:
                    st.info("No skipped loops.")
