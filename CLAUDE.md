# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QA evaluation pipeline that analyzes voice AI agent system prompts and extracts conversation flow logic as Finite State Machines (FSMs). Uses Claude Opus 4.5 with extended thinking to reverse-engineer system prompts into structured FSM representations.

## Pipeline Architecture

Three sequential scripts:

1. **FSM Generation** (`script_1_gen.py`): Calls Claude API with extended thinking to analyze prompts → `output.json`
2. **Visualization** (`script_2_viz.py`): Converts FSM JSON to Graphviz flowchart → `flowchart.png` + DOT source
3. **Path Analysis** (`script_3_ana.py`): Finds all paths through FSM, clusters into archetypes (P0), major variations (P1), minor differences (P2) → `clustered_flow_report.txt` + `.xlsx`

**Key Parameters:**
- Clustering thresholds: P2 (95% similarity), P1 (70% similarity)
- Entry/Exit states: `STATE_GREETING` → `STATE_END_CONVERSATION`

## Architecture

### Core Services

- **FileManager** (`utils/file_manager.py`): Session-isolated file operations in `outputs/{session_id}/`
- **DatabaseClient** (`utils/database_client.py`): Singleton Supabase client for persistent storage
- **HistoryManager** (`utils/history_manager.py`): Database CRUD for run history (PostgreSQL)
- **HistoryService** (`services/history_service.py`): Business logic for saving/loading runs
  - `save_current_run()` → returns dict with Supabase URLs (`flowchart_png_path`, `excel_report_path`) and text content (`flowchart_dot_path`, `report_text`)
  - Uploads files to Supabase Storage, deletes local `outputs/{session_id}/`
- **StreamingService**, **VisualizationService**, **AnalysisService**: Wrap scripts with session-based file operations
- **ExcelService**: Generates `.xlsx` exports (non-fatal failures)
- **ReportParser**: Parses text reports into structured `Cluster` objects

### Main Application (`app.py`)

**View Modes:**
- `new_run`: Pipeline execution with "Save to History" button
- `history_table`: List of saved runs
- `history_detail`: Read-only view of historical run

**Save Flow:**
1. User clicks "Save to History" → Files uploaded to Supabase Storage
2. Metadata saved to database, local files deleted
3. Session state updated with Supabase URLs (critical for continued viewing)

## Configuration

### Environment Variables (`.env`)
```bash
ANTHROPIC_API_KEY=your_api_key_here
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key  # Use service_role, not anon key
```

### Supabase Setup
Required for run history persistence. Create:
1. **Database table `runs`**: Stores metadata + text/JSON (see schema in migration history or `history_service.py`)
2. **Storage bucket `run-artifacts`**: Public bucket for PNG/XLSX files
3. Disable RLS (service_role key has admin access)

## Key Implementation Details

### Session State Path Update After Save
**Critical Fix**: After saving to history, `save_dialog.py` captures the dict returned by `save_current_run()` and updates session state:
- `flowchart_png_path` → Supabase Storage URL
- `flowchart_dot_path` → DOT source text content
- `report_path` → Temporary file (created with `tempfile`)
- `excel_report_path` → Supabase Storage URL or None

**Why**: Local files are deleted after upload. Without updating paths, UI crashes with `MediaFileStorageError`.

### Run History (Supabase Migration)
- **Before**: Local `history/` directories (ephemeral on Streamlit Cloud)
- **After**: Supabase PostgreSQL + Storage (persistent)
- **File Handling**: PNG/XLSX in Storage bucket, text/JSON in database columns
- **UI**: Download buttons handle both URLs (historical) and local paths (active runs)

### Null Transition Validation
`script_2_viz.py` filters transitions with null `to_state`/`trigger_intent` before graphviz rendering.

## Running the Pipeline

```bash
# CLI
python master_pipeline.py

# Individual scripts
python script_1_gen.py
python script_2_viz.py
python script_3_ana.py

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
├── script_1_gen.py, script_2_viz.py, script_3_ana.py
├── app.py (Streamlit UI)
├── utils/ (file_manager, session_state, database_client, history_manager)
├── services/ (streaming, visualization, analysis, excel, report_parser, history_service)
├── components/ (execution_zone, analysis_zone, visual_zone, results_zone, save_dialog, history_table)
└── outputs/{session_id}/ (ephemeral, deleted after save to Supabase)
```

## Error Handling

- **Script 1**: Validates non-empty output, checks JSON structure
- **Script 2**: Filters invalid transitions, saves diagnostic JSON on failure
- **Script 3**: Validates DOT format, handles disconnected graphs
- **Excel Export**: Non-fatal (failure shows warning, disables download button)
- **Master Pipeline**: Fail-fast (subprocess with `check=True`)
