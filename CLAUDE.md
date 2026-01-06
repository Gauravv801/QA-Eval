# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QA evaluation pipeline that analyzes voice AI agent system prompts and extracts conversation flow logic as Finite State Machines (FSMs). Uses Claude Opus 4.5 with extended thinking to reverse-engineer system prompts into structured FSM representations.

## Pipeline Architecture

Sequential steps:

1. **FSM Generation** (`script_1_gen.py`): Calls Claude API with extended thinking to analyze prompts → `output.json`
2. **Static Visualization** (`script_2_viz.py`): Converts FSM JSON to Graphviz flowchart → `flowchart.png` + DOT source
3. **Interactive Visualization** (`script_viz_interactive.py`): Creates pre-positioned NetworkX graph with PyVis rendering → `flowchart_interactive.html`
4. **Path Analysis** (`script_3_ana.py`): Finds all paths through FSM, clusters into archetypes (P0), major variations (P1), minor differences (P2) → `clustered_flow_report.txt` + `.xlsx`

**Key Parameters:**
- Clustering thresholds: P2 (95% similarity), P1 (70% similarity)
- Entry/Exit states: `STATE_GREETING` → `STATE_END_CONVERSATION`

## Architecture

### Core Services

- **FileManager** (`utils/file_manager.py`): Session-isolated file operations in `outputs/{session_id}/`
- **DatabaseClient** (`utils/database_client.py`): Singleton Supabase client for persistent storage
- **HistoryManager** (`utils/history_manager.py`): Database CRUD for run history (PostgreSQL)
- **HistoryService** (`services/history_service.py`): Business logic for saving/loading runs
  - `save_current_run()` → returns dict with Supabase URLs (`flowchart_png_path`, `flowchart_html_path`, `excel_report_path`) and text content (`flowchart_dot_path`, `report_text`)
  - Uploads files to Supabase Storage (PNG, HTML, XLSX), deletes local `outputs/{session_id}/`
- **StreamingService**, **VisualizationService**, **AnalysisService**: Wrap pipeline scripts with session-based file operations
- **InteractiveVisualizationService** (`services/interactive_visualization_service.py`): Wraps `script_viz_interactive.py`, generates HTML in temp location then moves to session directory
- **ExcelService**: Generates `.xlsx` exports (non-fatal failures)
- **ReportParser**: Parses text reports into structured `Cluster` objects

### UI Components

- **interactive_zone** (`components/interactive_zone.py`): Renders interactive HTML visualizations
  - Uses `streamlit.components.v1.html()` for iframe embedding
  - Dual-mode support: local files (active runs) vs Supabase URLs (historical runs)
  - Fetches HTML once (via HTTP for Supabase URLs, file read for local)
  - **Optimized**: Reuses fetched content for both iframe and download (no duplicate requests)
  - Provides `st.download_button()` for both modes (forces browser download with `Content-Disposition: attachment` headers)

### Main Application (`app.py`)

**View Modes:**
- `new_run`: Pipeline execution with "Save to History" button (4 tabs)
- `history_table`: List of saved runs
- `history_detail`: Read-only view of historical run (4 tabs)

**Tabs (both new_run and history_detail):**
1. LLM Output: Thinking console + cost metrics + JSON output
2. Flowchart: Static PNG visualization + DOT source
3. Interactive: Embeds HTML visualization with drag/zoom controls
4. Clustered Paths: Path analysis report + Excel download

**Save Flow:**
1. User clicks "Save to History" → Files uploaded to Supabase Storage (PNG, HTML, XLSX)
2. Metadata saved to database, local `outputs/{session_id}/` deleted
3. Session state paths updated to Supabase URLs (critical for continued viewing)

## Configuration

### Environment Variables (`.env`)
```bash
ANTHROPIC_API_KEY=your_api_key_here
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key  # Use service_role, not anon key
```

### Supabase Setup
Required for run history persistence. Create:
1. **Database table `runs`**: Stores metadata + text/JSON (includes `flowchart_html_path` column)
2. **Storage bucket `run-artifacts`**: Public bucket for PNG/HTML/XLSX files
3. Disable RLS (service_role key has admin access)
4. **Important**: Files must have correct `contentType` metadata for browser rendering

## Key Implementation Details

### Session State Path Update After Save
**Critical Fix**: After saving to history, `save_dialog.py` captures the dict returned by `save_current_run()` and updates session state:
- `flowchart_png_path` → Supabase Storage URL
- `flowchart_html_path` → Supabase Storage URL (interactive visualization)
- `flowchart_dot_path` → DOT source text content
- `report_path` → Temporary file (created with `tempfile`)
- `excel_report_path` → Supabase Storage URL or None

**Why**: Local files are deleted after upload. Without updating paths, UI crashes with `MediaFileStorageError`.

### Run History Persistence
- **Storage**: Supabase PostgreSQL (metadata/text/JSON) + Storage bucket (PNG/HTML/XLSX files)
- **Dual-Mode UI**: Components handle both local file paths (active runs) and Supabase URLs (historical runs)

### Content-Type Configuration for HTML Files
**Critical**: Supabase Python SDK requires camelCase `contentType` in `file_options` parameter:
```python
file_options={
    "contentType": self._get_mime_type(filename),  # Must be camelCase, not kebab-case
    "cacheControl": "3600",
    "upsert": "true"
}
```
Without correct format, HTML files are served as `text/plain` instead of rendering in browser.

### Null Transition Validation
`script_2_viz.py` filters transitions with null `to_state`/`trigger_intent` before graphviz rendering.

### Parallel Edge Handling (Critical for Visualization Consistency)
**Problem**: FSMs often have multiple transitions between the same state pairs with different trigger intents. Example: 10 different reasons to transition from `STATE_DELIVER_MAIN_MESSAGE` → `STATE_END_CONVERSATION`.

**Static Visualization** (`script_2_viz.py`):
- Graphviz `dot.edge()` naturally supports parallel edges
- Each call creates a separate visual arrow
- All transitions visible by default

**Interactive Visualization** (`script_viz_interactive.py`):
- **Line 79**: Uses `nx.MultiDiGraph()` (NOT `nx.DiGraph()`)
  - `DiGraph` only stores one edge per node pair → data loss
  - `MultiDiGraph` stores all parallel edges with unique keys
- **Line 176**: Uses `smooth: {"type": "dynamic"}` for vis.js
  - Fixed curve types (`"cubicBezier"`, `"curvedCW"`) draw parallel edges on same path → visual overlap
  - `"dynamic"` automatically calculates different curve offsets → visually distinct arrows

**Critical**: Without both fixes, interactive visualization shows only 1 edge where static shows 10+, appearing as data loss to users.

### Interactive HTML Download Implementation
**Problem Solved**: HTML files with `Content-Type: text/html` are rendered by browsers when navigated to via hyperlinks, not downloaded.

**Solution** (`components/interactive_zone.py`):
- Fetches HTML content once for both iframe preview and download
- Uses `st.download_button()` for both active (local files) and historical runs (Supabase URLs)
- `st.download_button()` sends `Content-Disposition: attachment` headers → forces download instead of rendering
- **Performance optimization**: Reuses content already fetched for iframe, avoiding duplicate network requests

**Why markdown links don't work**: Plain `<a href="...">` links cause browser navigation. For HTML files, browsers render the content instead of downloading it. Using `st.download_button()` provides consistent download behavior across both local and remote files.

## Running the Pipeline

```bash
# CLI (runs all 4 scripts sequentially)
python master_pipeline.py

# Individual scripts
python script_1_gen.py                  # FSM generation
python script_2_viz.py                  # Static visualization (PNG)
python script_viz_interactive.py        # Interactive visualization (HTML)
python script_3_ana.py                  # Path analysis

# Web UI
streamlit run app.py
```

## Quick Configuration Changes

**Change Claude model** (`script_1_gen.py:28`):
```python
model="claude-opus-4-5-20251101"
```

**Adjust clustering** (`script_3_ana.py:72-74`):
```python
THRESHOLD_P2_IDENTICAL = 0.95
THRESHOLD_P1_VARIATION = 0.7
```

**Change start/end states** (`script_3_ana.py:225-226`):
```python
start_node = "STATE_GREETING"
end_node = "STATE_END_CONVERSATION"
```

## Project Structure

```
QA_Eval/
├── script_1_gen.py, script_2_viz.py, script_viz_interactive.py, script_3_ana.py
├── master_pipeline.py (CLI orchestrator)
├── app.py (Streamlit UI)
├── utils/ (file_manager, session_state, database_client, history_manager)
├── services/ (streaming, visualization, interactive_visualization, analysis, excel, report_parser, history_service)
├── components/ (execution_zone, analysis_zone, visual_zone, interactive_zone, results_zone, save_dialog, history_table, top_navigation)
└── outputs/{session_id}/ (ephemeral, deleted after save to Supabase)
```

## Error Handling

**Pipeline Scripts:**
- **Script 1 (Generation)**: Validates non-empty output, checks JSON structure
- **Script 2 (Static Viz)**: Filters invalid transitions, saves diagnostic JSON on failure. Supports parallel edges via Graphviz.
- **Script 3 (Interactive Viz)**: Uses MultiDiGraph for parallel edge support, dynamic smoothing for visual distinction. Non-fatal - pipeline continues, error shown in UI tab.
- **Script 4 (Analysis)**: Validates DOT format, handles disconnected graphs
- **Master Pipeline CLI**: Fail-fast mode (subprocess with `check=True`)

**Non-Fatal Failures (Web UI):**
- Interactive visualization errors don't block pipeline (static PNG remains available)
- Excel generation failures show warning but allow save to history
- Errors persisted in session state for display after rerun

## Interactive Visualization Technical Details

The interactive HTML flowchart (`script_viz_interactive.py`) uses a hybrid layout approach:

**Graph Structure (Line 79):**
- **NetworkX MultiDiGraph**: Supports parallel edges (multiple transitions between same state pairs)
- Critical for FSMs with multiple trigger intents for the same state transition
- Example: 10 different ways to go from `STATE_DELIVER_MAIN_MESSAGE` → `STATE_END_CONVERSATION`

**Layout Strategy:**
- **Pre-positioning**: Uses GraphViz `dot` engine to calculate hierarchical node positions
- **Fallback**: If PyGraphviz/PyDot unavailable, falls back to NetworkX spring layout
- **Physics Disabled**: PyVis physics engine disabled to preserve GraphViz positions
- **Manual Dragging**: Nodes can be repositioned manually (positions aren't saved)
- **Coordinate Scaling**: Applies 1.5x scale factor for better spacing, inverts Y-axis for top-down flow

**Rendering:**
- **Parallel Edge Support**: Dynamic edge smoothing automatically curves parallel edges differently to avoid visual overlap
- Edge labels truncated to 20 chars (full text visible on hover)
- Navigation buttons, zoom, and pan controls enabled
- Color-coded nodes: Green (START/GREETING), Red (END), Blue (default states)

**Edge Smoothing (Line 176):**
- Uses `"dynamic"` smooth type for vis.js rendering
- Automatically detects multiple edges between same nodes and assigns different curve offsets
- Each parallel edge renders as a visually distinct curved arrow
- **Critical**: Fixed curve types like `"cubicBezier"` or `"curvedCW"` would cause parallel edges to overlap and appear as a single edge

**Technology**: NetworkX MultiDiGraph (graph structure) + GraphViz (layout) + PyVis (interactive rendering) + vis.js (dynamic edge smoothing)
