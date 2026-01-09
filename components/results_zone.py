import streamlit as st
import os


def render_results_zone_priority(priority_collection, report_path):
    """Render stats-only dashboard (no individual path rendering)."""

    st.markdown("---")
    st.subheader("📊 Path Analysis Summary")

    # Excel error warning
    if st.session_state.excel_error:
        st.warning(
            f"**Excel export failed**: {st.session_state.excel_error}\n\n"
            "The text report is available, but the Excel (.xlsx) download is unavailable."
        )

    # Safe stats extraction with None check
    if priority_collection is not None and hasattr(priority_collection, 'stats'):
        stats = priority_collection.stats
        total_paths = stats.get('p0_count', 0) + stats.get('p1_count', 0) + stats.get('p2_count', 0) + stats.get('p3_count', 0)

        # Metrics dashboard (4 columns)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("P0 (Base Paths)", stats.get('p0_count', 0))
        with col2:
            st.metric("P1 (Logic Variations)", stats.get('p1_count', 0))
        with col3:
            st.metric("P2 (Loop Tests)", stats.get('p2_count', 0))
        with col4:
            st.metric("P3 (Supplemental)", stats.get('p3_count', 0))

        # Coverage summary section
        st.markdown("---")
        st.markdown("### Test Coverage Summary")
        total_meaningful = stats.get('p0_count', 0) + stats.get('p1_count', 0) + stats.get('p2_count', 0)
        coverage_pct = (total_meaningful / total_paths * 100) if total_paths > 0 else 0

        st.info(f"""
        **Optimized Test Suite:** {total_meaningful} / {total_paths} paths ({coverage_pct:.1f}% coverage)
        - **{stats.get('p3_count', 0)} redundant paths** archived to reduce QA effort
        - Download reports below to view individual paths
        """)
    else:
        # Legacy run or missing stats - show message directing to downloads
        st.info("""
        **Path statistics not available for this run.**

        This may be a legacy run or stats were not generated. Download the reports below to view path details.
        """)

    # Download buttons (always available, even for legacy runs)
    st.markdown("---")
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
