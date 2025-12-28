# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a QA evaluation pipeline for analyzing voice AI agent system prompts and extracting their conversation flow logic as Finite State Machines (FSMs). The pipeline uses Claude's extended thinking capabilities to reverse-engineer system prompts into structured FSM representations with states, intents, and transitions.

## Pipeline Architecture

The system consists of three sequential scripts orchestrated by a master pipeline:

### Script 1: FSM Generation (`script_1_gen.py`)
- **Purpose**: Calls Claude Opus 4.5 with extended thinking to analyze system prompts
- **Input** (CLI mode): `prompt.txt` (contains system instructions + user prompt separated by `---SEP---`)
- **Input** (UI mode): Two separate fields - FSM extraction instructions + voice agent prompt
- **Output**: `output.json` (raw FSM extraction with vocabulary, states, intents, transitions)
- **Key Features**: Uses streaming API with `thinking` enabled (45k token budget), calculates API costs
- **Pricing**: $5/1M input tokens, $25/1M output tokens (Claude Opus 4.5)

### Script 2: Visualization (`script_2_viz.py`)
- **Purpose**: Converts FSM JSON into visual flowchart
- **Input**: `LLM_output_axis.json` (bridged from Script 1's output)
- **Output**: `flowchart_claude` (DOT source) + `flowchart_claude.png` (rendered image)
- **Technology**: Uses Graphviz with top-to-bottom layout, rounded nodes
- **Validation**: Filters out transitions with null/missing required fields to prevent graphviz errors

### Script 3: Path Analysis (`script_3_ana.py`)
- **Purpose**: Analyzes all possible conversation paths through the FSM
- **Input**: `flowchart_collections_std` (bridged from Script 2's DOT source)
- **Output**: `clustered_flow_report.txt` (grouped conversation archetypes) + `clustered_flow_report.xlsx` (Excel export)
- **Algorithm**: Parses DOT format, finds all paths from `STATE_GREETING` to `STATE_END_CONVERSATION`, clusters paths into P0 (archetypes), P1 (major variations), P2 (minor differences)
- **Clustering Thresholds**: P2 (95% similarity), P1 (70% similarity)

## Service Layer Architecture

All services follow the same pattern: receive `FileManager` instance in constructor, provide session-isolated file operations.

### Core Services

#### FileManager (`utils/file_manager.py`)
Manages session-isolated file operations. Creates `outputs/{session_id}/` directory.
- `get_path(filename)`: Returns session-scoped file path
- `save_json()`, `load_json()`, `save_text()`, `load_text()`

#### SessionStateManager (`utils/session_state.py`)
Centralized Streamlit session state management (22 variables):
- **Pipeline State**: `session_id`, `pipeline_running`, `current_step`, `thinking_text`, `output_text`, `output_json`, `cost_metrics`
- **Output Paths**: `flowchart_png_path`, `flowchart_dot_path`, `report_path`, `parsed_clusters`, `excel_report_path`, `excel_error`, `active_tab`
- **History Navigation**: `view_mode`, `current_history_session_id`, `show_save_dialog`, `history_agent_prompt`, `history_fsm_instructions`, `history_run_metadata`, `delete_confirmation_session_id`, `run_saved_to_history`

#### StreamingService (`services/streaming_service.py`)
Wraps `script_1_gen.generate_fsm()` with session-based file saving.
- `stream_generation()`: Executes FSM generation, returns `(json_data, cost_data)`

#### VisualizationService (`services/visualization_service.py`)
Wraps `script_2_viz.generate_flowchart()` with session-based output management.
- `create_flowchart(json_data)`: Returns `(png_path, dot_source_path)`

#### AnalysisService (`services/analysis_service.py`)
Wraps `script_3_ana.generate_path_analysis()` with session-based reporting.
- `analyze_paths(dot_source_path, start_node, end_node)`: Returns report file path

#### ExcelService (`services/excel_service.py`)
Generates Excel (.xlsx) exports from parsed cluster data with vertical path layout and descriptions.
- `generate_excel(clusters, vocabulary_json=None)`: Returns path to .xlsx file
- **Excel Structure**: One sheet per archetype, interleaved columns for each flow (Flow → Description → Blank separator)
- **Column Padding**: Variable-length paths auto-padded with None values to create equal-length DataFrame columns
- **Error Handling**: Non-fatal - failures stored in `excel_error` session state, displayed in results zone

#### ReportParser (`services/report_parser.py`)
Parses text-based clustered flow report into structured data for UI rendering.
- **Data Classes**: `PathSegment` (source, target, action), `Path` (segments + metadata), `Cluster` (P0 + P1/P2 variations)
- `parse()`: Returns list of `Cluster` objects

#### HistoryManager (`utils/history_manager.py`)
Low-level registry CRUD operations for run history management.
- `load_registry()`: Load `history/registry.json` with corruption recovery
- `save_registry()`: Atomic writes using temp file + rename
- `add_run(metadata)`: Append run to registry
- `get_run(session_id)`: Retrieve run metadata by session ID
- `delete_run(session_id)`: Remove run from registry
- `get_all_runs()`: Get all runs sorted by date descending (newest first)
- **Error Handling**: Backs up corrupted registry to `.backup.{timestamp}`, returns empty structure

#### HistoryService (`services/history_service.py`)
Business logic layer for managing run history.
- `save_current_run()`: Save with computed metadata (cost, paths, archetypes)
- `load_run_data(session_id)`: Load all artifacts from `outputs/{session_id}/` directory
- `get_history_table_data()`: Format runs for table display
- `delete_run_with_cleanup()`: Remove registry entry + delete session directory
- **Backward Compatibility**: Handles legacy runs without `agent_prompt.txt`/`fsm_instructions.txt`

### UI Components (`components/`)

All components use standard Streamlit elements with no custom styling:

- **ExecutionZone** (`execution_zone.py`): `render_thinking_console()` - Displays thinking process in basic expander
- **AnalysisZone** (`analysis_zone.py`): `render_analysis_zone()` - Standard metric cards and JSON viewer
- **VisualZone** (`visual_zone.py`): `render_visual_zone()` - Flowchart display with download buttons
- **ResultsZone** (`results_zone.py`): `render_results_zone()` - Path analysis with expandable clusters
- **TopNavigation** (`top_navigation.py`): `render_top_navigation()` - Sidebar navigation buttons
- **HistoryTable** (`history_table.py`): `render_history_table()` - History table with View/Delete actions, formatted dates (DD/MM/YY HH:MM), and notes display
- **SaveDialog** (`save_dialog.py`): `show_save_dialog()` - Modal dialog for saving runs with automatic path updates

### Main Application (`app.py`)

**Split-Field Input Design**: Two separate text areas (FSM extraction instructions auto-loaded from `prompt.txt`, voice agent prompt user-entered).

**Tabbed Results Interface**: Three tabs (LLM Output, Flowchart, Clustered Paths) for organized result display.

**Pipeline Execution**: Runs all 3 steps sequentially with real-time UI updates. Excel generation happens automatically after Step 3 (non-fatal on failure).

**View Mode Routing**: Three-mode architecture with sidebar navigation:
- **new_run**: Standard pipeline execution view with "View Run History" button in sidebar
- **history_table**: Interactive table showing all saved runs with "New Run" button in sidebar
- **history_detail**: Read-only view of historical run (reuses same 3-tab UI)

**Save to History**: Opt-in run persistence with "Save to History" button after pipeline completion. After saving, session state file paths are updated to point to the new `history/{session_id}/` location, and the button is replaced with a success message. This allows users to continue viewing results while preventing duplicate saves.

## Running the Pipeline

### Full Pipeline (CLI)
```bash
python master_pipeline.py
```

### Individual Scripts
```bash
python script_1_gen.py  # FSM generation
python script_2_viz.py  # Flowchart visualization
python script_3_ana.py  # Path analysis
```

### Web UI (Streamlit)
```bash
streamlit run app.py
```

**How to Use**:
1. Field 1: FSM extraction instructions (auto-populated from `prompt.txt`)
2. Field 2: Voice agent system prompt (paste your prompt here)
3. Click "Generate Test Cases" → Pipeline runs all 3 steps → Results in tabs
4. **Save to History** (optional): Click "Save to History" button, add notes, confirm → Files moved to `history/` and button replaced with success message
5. **View History**: Click "View Run History" in sidebar → Browse saved runs → Click "View" to open read-only historical run

**Downloads Available**:
- **LLM Output Tab**: Raw JSON
- **Flowchart Tab**: PNG and DOT source
- **Clustered Paths Tab**: TXT (plain text) and XLSX (Excel spreadsheet)

## Dependencies

```bash
pip install -r requirements.txt
```

**Required**:
- `anthropic>=0.18.0` - Claude API client
- `python-dotenv>=1.0.0` - Environment variable management
- `graphviz>=0.20.1` - Flowchart rendering (Python bindings)
- `networkx>=3.2.1` - Graph analysis for path finding
- `streamlit>=1.31.0` - Web UI framework
- `Pillow>=10.2.0` - Image handling for UI
- `pandas>=2.0.0` - Excel export with DataFrame construction
- `openpyxl>=3.1.0` - Excel file writing engine

**System Requirements**:
- Python 3.9 or higher
- Graphviz system library (macOS: `brew install graphviz`, Ubuntu: `sudo apt-get install graphviz`)

## Configuration

### Environment Variables
Create a `.env` file with:
```
ANTHROPIC_API_KEY=your_api_key_here
```

**SECURITY NOTE**: The `.env` file contains a live API key and should NEVER be committed to version control.

### Prompt Format (`prompt.txt`) - CLI Mode Only
```
[FSM Extraction Instructions]
---SEP---
#####SYSTEM_PROMPT
[Voice agent system prompt to analyze]
```

**Note**: Web UI uses split-field design instead of `---SEP---` delimiter.

## FSM Extraction Rules (Core Logic)

Key principles from `prompt.txt`:

1. **Holistic Analysis**: Logic is distributed across the prompt (not just "Conversation Flow" sections)
2. **Vocabulary Extraction**: User Intents (`USER_[ACTION]`), Bot States (`STATE_[MODE]`), Tools (`TOOL_[NAME]`)
3. **Transition Mapping**: Double-check protocol (forward + reverse scan)
4. **Entry/Exit Constraints**: Initial state = `STATE_GREETING`, Terminal state = `STATE_END_CONVERSATION`
5. **Quality Assurance**: Paragraph sweep, orphan state check, dead-end check

## Output Artifacts

### CLI Mode (master_pipeline.py)
Outputs saved to project root:
- `output.json`, `cost_metrics.json`, `LLM_output_axis.json`
- `flowchart_claude`, `flowchart_claude.png`, `flowchart_collections_std`
- `clustered_flow_report.txt`

### UI Mode (FileManager)
Session-isolated outputs in `outputs/{session_id}/`:
- `output.json`, `cost_metrics.json`, `flowchart.png`, `flowchart_source`
- `clustered_flow_report.txt`, `clustered_flow_report.xlsx`, `thinking.txt`
- `agent_prompt.txt`, `fsm_instructions.txt` (for historical retrieval)

### Run History
Persistent history storage in `history/`:
- `registry.json` - Metadata for all saved runs (timestamp, prompt preview, notes, cost, paths)

## Error Handling

### Script-Level Behavior
- **Script 1**: Validates non-empty text output, checks JSON structure
- **Script 2**: Filters null/missing transitions before graphviz, saves diagnostic JSON on failures
- **Script 3**: Validates DOT format, handles missing nodes/disconnected graphs
- **Excel Export**: Non-fatal failures, shows warning in UI, disabled XLSX button

### Master Pipeline
Fail-fast behavior: Each script runs as subprocess with `check=True`, stops immediately on failure.

## Key Features & Fixes

### Null Transition Validation (script_2_viz.py)
**Fix**: Filters transitions with null `to_state`/`trigger_intent` before passing to graphviz. Terminal states don't need outgoing edges.

### Excel Export Feature
**Added**: Excel (.xlsx) export alongside TXT download for spreadsheet-based analysis.
- **Structure**: One sheet per archetype, columns for P0/P1.x/P2.x with descriptions, vertical flow format
- **Path Flattening**: Converts PathSegment lists to vertical arrays
- **Auto-Alignment**: Shorter paths padded with blank cells via pandas DataFrame

### Excel DataFrame Padding Fix
**Fix**: Resolved "At least one sheet must be visible" error caused by unequal column lengths.
- Pad shorter columns with None values to match max length before DataFrame creation

### Run History Feature
**Added**: User-controlled run history with opt-in persistence and historical run viewing.

**Architecture**:
- **Storage**: JSON registry at `history/registry.json` with metadata for all saved runs
- **Session Directories**: Moved from `outputs/{session_id}/` to `history/{session_id}/` when saved
- **View Modes**: Three-mode routing (new_run, history_table, history_detail)

**Features**:
- **Opt-in Saving**: Only saves when user clicks "Save to History" button
- **Metadata Table**: Formatted date (DD/MM/YY HH:MM), prompt preview with notes below in muted text, cost, P0 count, path count
- **Read-Only View**: Same 3-tab UI, all action buttons disabled
- **Delete with Confirmation**: Removes registry entry + session directory
- **Backward Compatible**: Works with legacy sessions

### Path Update on Save Fix
**Fix**: Resolved MediaFileStorageError when viewing results after saving to history.
- **Problem**: After save, files moved to `history/` but session state still referenced `outputs/` paths
- **Solution**: `save_dialog.py` now updates all file paths in session state to absolute paths pointing to `history/{session_id}/` after successful save
- **UX Improvement**: "Save to History" button replaced with success message (✓ Run saved to history) to prevent duplicate saves and confirm action
- **Session State**: Added `run_saved_to_history` (bool) to track save status

### Serial Number Removal
**Simplification**: Removed serial number tracking from run history system.
- **Removed Components**: `next_serial` counter, `serial_number` field, `saved_run_serial` session state variable
- **UI Changes**: History table displays timestamp instead of "Run #X", delete confirmation shows date instead of serial
- **Registry Schema**: Simplified to contain only `runs` array (no `next_serial` field)
- **Benefits**: Simpler codebase, no counter management, runs identified by timestamp and session ID
- **Backward Compatibility**: Existing runs with `serial_number` in metadata continue to work (field ignored)

### Date/Time Formatting and Notes Display
**Improvement**: Enhanced history table readability with better date formatting and visible notes.
- **Date Format**: Changed from ISO 8601 (`2025-12-28T18:23`) to user-friendly DD/MM/YY HH:MM format (`28/12/25 18:23`)
- **Notes Display**: User-added notes now visible in history table below prompt preview in muted gray text
- **Implementation**: `format_datetime()` helper function in `history_table.py` converts ISO timestamps
- **Locations**: Applied to history table, delete confirmation dialog, and historical run metadata banner
- **Benefits**: Easier to scan dates at a glance, notes provide immediate context without opening the run

**Registry Schema**:
```json
{
  "runs": [
    {
      "session_id": "uuid",
      "saved_at": "ISO 8601 timestamp (displayed as DD/MM/YY HH:MM in UI)",
      "agent_prompt_preview": "first 100 chars",
      "notes": "user notes (displayed below prompt in history table)",
      "total_cost_usd": 0.0234,
      "num_archetypes": 2,
      "num_total_paths": 120
    }
  ]
}
```

## Project Structure

```
QA_Eval/
├── .env, .gitignore, CLAUDE.md, requirements.txt, prompt.txt
├── master_pipeline.py, script_1_gen.py, script_2_viz.py, script_3_ana.py
├── app.py (Main Streamlit UI with view mode routing)
├── utils/
│   ├── file_manager.py (Session-isolated file operations)
│   ├── session_state.py (Session state management)
│   └── history_manager.py (Registry CRUD operations)
├── services/
│   ├── streaming_service.py (FSM generation wrapper)
│   ├── visualization_service.py (Flowchart generation wrapper)
│   ├── analysis_service.py (Path analysis wrapper)
│   ├── excel_service.py (Excel export with descriptions)
│   ├── report_parser.py (Text report → structured data)
│   └── history_service.py (Run history business logic)
├── components/
│   ├── execution_zone.py (Thinking console)
│   ├── analysis_zone.py (Metric cards + JSON viewer)
│   ├── visual_zone.py (Flowchart display)
│   ├── results_zone.py (Path analysis)
│   ├── top_navigation.py (Sidebar navigation)
│   ├── history_table.py (History table)
│   └── save_dialog.py (Save run modal)
├── history/
│   └── registry.json (Run metadata storage)
├── outputs/{session_id}/
│   ├── output.json, cost_metrics.json, thinking.txt, raw_response.txt
│   ├── flowchart.png, flowchart_source
│   ├── clustered_flow_report.txt, clustered_flow_report.xlsx
│   ├── agent_prompt.txt
│   └── fsm_instructions.txt
└── [CLI outputs] (root directory)
```

## Modifying the Pipeline

### Change Claude Model
In `script_1_gen.py:28`:
```python
model="claude-opus-4-5-20251101"  # Update model ID
```

### Adjust Clustering Sensitivity
In `script_3_ana.py:72-74`:
```python
THRESHOLD_P2_IDENTICAL = 0.95  # Higher = stricter P2 grouping
THRESHOLD_P1_VARIATION = 0.7   # Higher = stricter P1 grouping
```

### Change Start/End States
In `script_3_ana.py:225-226`:
```python
start_node = "STATE_GREETING"
end_node = "STATE_END_CONVERSATION"
```
