# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QA evaluation pipeline that analyzes voice AI agent system prompts and extracts conversation flow logic as Finite State Machines (FSMs). Uses Claude Opus 4.5 with extended thinking to reverse-engineer system prompts into structured FSM representations.

## Pipeline Architecture

Sequential steps:

1. **FSM Generation** (`script_1_gen.py`): Calls Claude API with extended thinking to analyze prompts → `output.json`
2. **Static Visualization** (`script_2_viz.py`): Converts FSM JSON to Graphviz flowchart → `flowchart.png` + DOT source
3. **Interactive Visualization** (`script_viz_interactive.py`): Creates pre-positioned NetworkX graph with PyVis rendering → `flowchart_interactive.html`
4. **Path Analysis & Prioritization** (`script_3_ana.py`): Finds all paths through FSM, uses Greedy Set-Cover Algorithm to prioritize into 4 buckets → `clustered_flow_report.txt` + `.xlsx`
   - **P0 (Base Paths)**: Unique conversation archetypes - core flows
   - **P1 (Logic Variations)**: Paths covering new edge logic not in P0
   - **P2 (Loop Tests)**: Paths testing self-loop transitions
   - **P3 (Supplemental)**: Redundant paths fully covered by P0/P1/P2

**Key Parameters:**
- Clustering thresholds: P2 (95% similarity), P1 (70% similarity) - used for initial grouping before prioritization
- Entry/Exit states: `STATE_GREETING` → `STATE_END_CONVERSATION`

## Architecture

### Core Services

- **FileManager** (`utils/file_manager.py`): Session-isolated file operations in `outputs/{session_id}/`
  - Uses `Path(base_location).resolve()` to ensure absolute paths from initialization
  - All returned paths are absolute, preventing subprocess path resolution errors
- **DatabaseClient** (`utils/database_client.py`): Singleton Supabase client for persistent storage
- **HistoryManager** (`utils/history_manager.py`): Database CRUD for run history (PostgreSQL)
- **HistoryService** (`services/history_service.py`): Business logic for saving/loading runs
  - `save_current_run()` → handles both `PriorityPathCollection` (new) and `List[Cluster]` (legacy) formats
  - `load_run_data()` → auto-detects format from report text (`'=== [P0] GOLDEN PATHS'` marker) and uses appropriate parser
  - Returns `is_priority_mode` flag to enable conditional UI rendering
  - Uploads files to Supabase Storage (PNG, HTML, XLSX), deletes local `outputs/{session_id}/`
- **StreamingService** (`services/streaming_service.py`): Wraps `script_1_gen.py` using subprocess isolation
  - Uses subprocess execution to isolate memory (100-150MB freed after completion)
  - Writes `prompt.txt` with system prompt + user message
  - Reads `output.json` and `cost_metrics.json`
  - **Trade-off**: Thinking text not available (script doesn't write it in CLI mode)
  - **Critical**: Uses absolute path to script with `cwd=session_dir` for file I/O
- **VisualizationService** (`services/visualization_service.py`): Wraps `script_2_viz.py` using subprocess isolation
  - File bridging: copies `output.json` → `LLM_output_axis.json`
  - Reads `flowchart_claude.png` and `flowchart_claude` (DOT source)
- **InteractiveVisualizationService** (`services/interactive_visualization_service.py`): Wraps `script_viz_interactive.py` using subprocess isolation
  - Reads existing `output.json`, generates `flowchart_interactive.html`
  - Non-fatal error handling - failures don't block pipeline
- **AnalysisService** (`services/analysis_service.py`): Wraps `script_3_ana.py` using subprocess isolation
  - Returns tuple: `(stats_dict, report_path)` - **memory optimized**
  - File bridging: copies `flowchart_source` → `flowchart_collections_std`
  - Parses only stats from report header (not full paths)
  - Full path data parsed on-demand by `PriorityReportParser` for Excel generation
- **ExcelService** (`services/excel_service.py`): Generates `.xlsx` exports with dual-mode support
  - `generate_excel()` (legacy): Creates one sheet per archetype with interleaved P0/P1/P2 columns
  - `generate_excel_priority()` (new): Creates 4 separate tabs (P0_Base_Paths, P1_Logic_Variations, P2_Loops, P3_Supplemental)
  - Non-fatal failures - errors stored in session state
- **ReportParser** (`services/report_parser.py`): Contains all data models and parsers
  - **Legacy**: `Cluster`, `Path`, `PathSegment`, `ReportParser` (archetype-based format)
  - **New**: `PriorityPath`, `PriorityPathCollection`, `PriorityReportParser` (priority-based format)

### UI Components

- **interactive_zone** (`components/interactive_zone.py`): Renders interactive HTML visualizations
  - Uses `streamlit.components.v1.html()` for iframe embedding
  - Dual-mode support: local files (active runs) vs Supabase URLs (historical runs)
  - Fetches HTML once (via HTTP for Supabase URLs, file read for local)
  - **Optimized**: Reuses fetched content for both iframe and download (no duplicate requests)
  - Provides `st.download_button()` for both modes (forces browser download with `Content-Disposition: attachment` headers)
- **results_zone** (`components/results_zone.py`): Stats-only dashboard for path analysis (memory-optimized)
  - `render_results_zone_priority()`: Single rendering function (legacy removed for memory optimization)
  - Displays 4-metric dashboard (P0/P1/P2/P3 counts)
  - Shows coverage summary with optimization statistics
  - Provides download buttons for TXT and XLSX reports
  - **No individual path rendering**: Eliminates 150-200MB memory overhead from rendering thousands of DOM elements
  - Graceful degradation for legacy runs: Shows informational message when stats unavailable, download buttons always work
- **save_dialog** (`components/save_dialog.py`): Polymorphic metrics display
  - Handles both `PriorityPathCollection` and `List[Cluster]` formats using `hasattr(parsed_clusters, 'stats')` check
  - Shows "Archetypes/P0" and "Total Paths" correctly for both formats

### Main Application (`app.py`)

**View Modes:**
- `new_run`: Pipeline execution with "Save to History" button (4 tabs)
- `history_table`: List of saved runs
- `history_detail`: Read-only view of historical run (4 tabs)

**Tabs (both new_run and history_detail):**
1. LLM Output: Thinking console + cost metrics + JSON output
2. Flowchart: Static PNG visualization + DOT source
3. Interactive: Embeds HTML visualization with drag/zoom controls
4. Clustered Paths: **Stats-only dashboard** (memory-optimized)
   - 4-metric dashboard: P0 (Base Paths), P1 (Logic Variations), P2 (Loop Tests), P3 (Supplemental)
   - Coverage summary with test optimization statistics
   - Download buttons for TXT and XLSX reports
   - **No individual path rendering**: Saves 150-200MB by eliminating DOM elements for thousands of paths
   - Path details accessible via downloadable reports

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

### Path Prioritization with Greedy Set-Cover Algorithm

**Problem**: Old clustering approach (similarity-based) created too many paths for QA teams to test.

**Solution**: Implemented `prioritize_paths()` in `script_3_ana.py` using Greedy Set-Cover Algorithm to minimize path count while maximizing edge coverage.

**Algorithm Phases**:

1. **Phase 0 - Setup**: Construct universe of all edges (linear + loops) from all clustered paths
2. **Phase 1 - Golden Paths (P0)**: All archetype representatives (P0s from clustering) are automatically included
3. **Phase 2 - Greedy Discovery (P1)**: Iteratively select paths that cover the most uncovered linear edges
   - Score each candidate by count of unique uncovered edges
   - Tie-breaker: shortest path length
   - Continue until all linear edges covered or candidates exhausted
4. **Phase 3 - Loop Stress (P2)**: Select shortest path for each uncovered self-loop
5. **Phase 4 - Archive (P3)**: All remaining paths (redundant - fully covered by P0/P1/P2)

**Output Structure**:
```python
{
    "final_p0": [path_data, ...],  # Base Paths (Archetypes)
    "final_p1": [path_data, ...],  # Logic Variations (Greedy Cover)
    "final_p2": [path_data, ...],  # Loop Stress Tests
    "final_p3": [path_data, ...],  # Supplemental/Archive
    "skipped_edges": [...],
    "skipped_loops": [...],
    "stats": {"p0_count": int, "p1_count": int, "p2_count": int, "p3_count": int}
}
```

**Report Format**: Flat sections instead of hierarchical archetypes
- Section 1: `=== [P0] GOLDEN PATHS ===` (marker for format detection)
- Section 2: `=== [P1] REQUIRED VARIATIONS ===`
- Section 3: `=== [P2] LOOP STRESS TESTS ===`
- Section 4: `=== [P3] REDUNDANT PATHS ===`

### Data Architecture (Priority-Based Format)

**Design**: System uses priority-based format for all new runs. Legacy archetype-based format support removed from UI for memory optimization.

**Format Detection** (History Service):
- `HistoryService.load_run_data()` checks for `'=== [P0] GOLDEN PATHS'` in report text
- Sets `is_priority_mode` flag based on detection result
- Uses `PriorityReportParser` for new format, `ReportParser` for legacy

**Data Models**:
- **Legacy**: `Cluster` (hierarchical: P0 archetype with nested P1/P2 lists) - still supported in service layer for historical data
- **Current**: `PriorityPathCollection` (flat: separate lists for P0/P1/P2/P3) - used for all new runs

**Service Layer**:
- `script_3_ana.py` returns tuple: `(prioritized_dict, report_path)` instead of just string
- `AnalysisService` converts dict → `PriorityPathCollection`
- `HistoryService` handles both formats polymorphically using `hasattr(parsed_clusters, 'stats')`

**UI Rendering** (Memory-Optimized):
- Single rendering function: `render_results_zone_priority()` for all runs
- **No conditional dispatch**: Legacy format rendering removed to save memory
- Stats-only dashboard: Shows metrics when available, informational message for legacy runs
- Download buttons always functional for both new and legacy runs
- **Trade-off**: Legacy historical runs show stats unavailable message but retain full data access via downloads

**Excel Generation**:
- Legacy: `generate_excel()` → One sheet per archetype, interleaved columns (still used for old runs)
- Current: `generate_excel_priority()` → 4 separate tabs (P0_Base_Paths, P1_Logic_Variations, P2_Loops, P3_Supplemental)

**Naming Conventions**:
- P0: **Base Paths** (core conversation archetypes)
- P1: **Logic Variations** (major variations covering new edges)
- P2: **Loop Tests** (self-loop stress tests)
- P3: **Supplemental Paths** (redundant/archive)

### Session State Management

**Format Flag** (`utils/session_state.py`):
- `is_priority_mode` (bool): Tracks whether current run uses priority-based or archetype-based format
- Defaults to `False` for backward compatibility
- Set to `True` for new runs after analysis completes
- Loaded from database for historical runs via format auto-detection
- Used for Excel generation function selection (not used for UI rendering - single stats-only view for all formats)

**Path Update After Save**:
After saving to history, `save_dialog.py` captures the dict returned by `save_current_run()` and updates session state:
- `flowchart_png_path` → Supabase Storage URL
- `flowchart_html_path` → Supabase Storage URL (interactive visualization)
- `flowchart_dot_path` → DOT source text content
- `report_path` → Temporary file (created with `tempfile`)
- `excel_report_path` → Supabase Storage URL or None

**Why**: Local files are deleted after upload. Without updating paths, UI crashes with `MediaFileStorageError`.

### UI Memory Optimization

**Problem**: Streamlit app crashed with high memory usage when rendering 7,000+ individual paths in the UI.

**Root Cause**:
- Each path created multiple DOM elements (expanders, text blocks, code segments)
- For large FSMs, path rendering consumed 150-200MB of browser memory
- Browser tabs would freeze or crash during rendering

**Solution**: Stats-only dashboard (Layer 3 optimization)
- **Removed**: All individual path rendering from `components/results_zone.py`
  - Deleted `render_results_zone()` (legacy archetype function)
  - Deleted `render_path_text()` helper
  - Replaced `render_results_zone_priority()` with stats-only version
- **Retained**:
  - 4-metric dashboard (P0/P1/P2/P3 counts)
  - Coverage summary statistics
  - Download buttons for TXT and XLSX reports
- **Impact**:
  - Memory reduction: 150-200MB → <5MB (97-98% savings)
  - No browser crashes for large analyses
  - Faster page loads
  - All path details still accessible via downloadable reports

**Implementation Details**:
- `render_results_zone_priority()` checks for `priority_collection.stats` availability
- Shows metrics dashboard when stats present
- Shows informational message for legacy runs without stats
- Download buttons always rendered and functional
- No server-side path segment objects created for UI rendering

**Trade-offs Accepted**:
- Users can no longer browse individual paths interactively in the UI
- Must download TXT/XLSX reports to view path details
- Legacy historical runs show "stats unavailable" message instead of path list

### Subprocess Isolation (Layer 1 Optimization)

**Problem**: High memory usage from keeping backend script modules loaded in memory throughout Streamlit session.

**Solution**: Convert service layer from direct function imports to subprocess execution.

**Memory Savings**:
- Each subprocess exits and releases 100-150MB (NetworkX graphs, API responses, path objects)
- Stats-only storage saves 50-100MB in session state (vs full PriorityPathCollection)
- Total reduction: ~200-350MB per pipeline run

**Implementation Pattern** (all 4 services):
```python
# Get session directory path
session_dir = os.path.dirname(self.file_manager.get_path('dummy'))

# Calculate absolute path to script (project root)
project_root = os.path.dirname(os.path.dirname(session_dir))
script_path = os.path.join(project_root, 'script_1_gen.py')

# Ensure paths are absolute (defensive - added 2025-01)
script_path = os.path.abspath(script_path)
session_dir = os.path.abspath(session_dir)

# Run subprocess with absolute script path
subprocess.run(
    [sys.executable, script_path],  # Use absolute path
    cwd=session_dir,  # Files read/written here
    check=True,
    timeout=600,
    capture_output=True,
    text=True
)
```

**Critical Implementation Details**:
1. **Absolute Paths Required - Two-Layer Approach**:
   - **Layer 1 (FileManager)**: Uses `Path(base_location).resolve() / session_id` to create absolute paths at initialization
     - Converts relative `"outputs"` → absolute `/Users/username/QA_Eval/outputs`
     - All paths returned by `get_path()` are absolute
   - **Layer 2 (Services - Defensive)**: Each service explicitly calls `os.path.abspath()` on script_path and session_dir before subprocess
     - Guards against edge cases where paths might still be relative
     - Ensures subprocess always receives absolute paths regardless of working directory
   - **Why both layers**: FileManager fix solves root cause; defensive conversion provides fail-safe
   - `cwd=session_dir` changes working directory to `outputs/{session_id}/`
   - Without absolute script_path, subprocess would look in session dir → FileNotFoundError
   - Absolute path `project_root/script_1_gen.py` works correctly from any working directory
2. **File Bridging**: Scripts expect specific input filenames
   - Script 1: reads `prompt.txt`, writes `output.json` + `cost_metrics.json`
   - Script 2: reads `LLM_output_axis.json`, writes `flowchart_claude.png` + `flowchart_claude`
   - Script 3 (interactive): reads `output.json`, writes `flowchart_interactive.html`
   - Script 4 (analysis): reads `flowchart_collections_std`, writes `clustered_flow_report.txt`
3. **Working Directory**: `cwd=session_dir` ensures input/output files are in session directory
4. **Process Isolation**: Each script runs in separate process, exits after completion

**Trade-offs**:
- **Thinking text unavailable**: `script_1_gen.py` doesn't write thinking to file in CLI mode
- **No real-time streaming**: Subprocess blocks until completion
- **Acceptable**: JSON output, cost metrics, visualizations, and analysis fully preserved

**Services Modified**:
- `StreamingService`: Subprocess for `script_1_gen.py` (FSM generation)
- `VisualizationService`: Subprocess for `script_2_viz.py` (static flowchart)
- `InteractiveVisualizationService`: Subprocess for `script_viz_interactive.py` (interactive HTML)
- `AnalysisService`: Subprocess for `script_3_ana.py` (path analysis)

**App.py Changes**:
- Stores stats dict instead of full `PriorityPathCollection` (memory optimization)
- Parses full report on-demand using `PriorityReportParser` for Excel generation
- Handles missing `thinking.txt` gracefully with informational messages

**HistoryService Changes**:
- Handles three formats: stats dict (new), `PriorityPathCollection` (transitional), `List[Cluster]` (legacy)
- Makes `thinking.txt` optional (defaults to empty string if not found)

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

**Adjust clustering thresholds** (`script_3_ana.py:63-64`):
```python
THRESHOLD_P2_IDENTICAL = 0.95  # Initial clustering before prioritization
THRESHOLD_P1_VARIATION = 0.7
```

**Change start/end states** (`script_3_ana.py:67-68`):
```python
_START_NODE = "STATE_GREETING"
_END_NODE = "STATE_END_CONVERSATION"
```

**Note**: The Greedy Set-Cover prioritization logic runs automatically after clustering. Adjust clustering thresholds to control initial grouping before prioritization.

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
- **Script 4 (Analysis & Prioritization)**:
  - Validates DOT format, handles disconnected graphs
  - Returns tuple `(prioritized_dict, report_path)` instead of just string
  - Clustering phase creates archetypes, then prioritization phase applies Greedy Set-Cover
  - Skipped edges/loops tracked and reported in warning section
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
