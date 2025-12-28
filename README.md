# QA_Eval - Voice AI Agent FSM Extraction Pipeline

A powerful QA evaluation pipeline that analyzes voice AI agent system prompts and extracts their conversation flow logic as Finite State Machines (FSMs). Uses Claude Opus 4.5's extended thinking capabilities to reverse-engineer system prompts into structured FSM representations with states, intents, and transitions.

## Overview

QA_Eval transforms unstructured voice AI system prompts into actionable test cases by:

1. **Analyzing** system prompts using Claude Opus 4.5 with extended thinking (45k token budget)
2. **Extracting** structured FSM representations (vocabulary, states, intents, transitions)
3. **Visualizing** conversation flows as interactive flowcharts
4. **Analyzing** all possible conversation paths and clustering them into archetypes

**Use Cases:**
- QA testing for voice AI agents
- Conversation flow analysis and optimization
- System prompt validation and debugging
- Documentation of agent behavior patterns

## Features

- **FSM Generation with Extended Thinking**: Leverages Claude Opus 4.5 with 45k token thinking budget for deep analysis
- **Graphviz-based Flowchart Visualization**: Generates visual graphs with rounded nodes and top-to-bottom layout
- **Path Analysis and Clustering**: Identifies conversation archetypes (P0), major variations (P1), and minor differences (P2)
- **Interactive Web UI**: Streamlit-based interface with session management and tabbed results
- **Run History with Opt-in Persistence**: Save and revisit previous analyses with notes
- **Multi-format Export**: JSON, PNG, DOT, TXT, and XLSX (Excel) formats
- **Cost Tracking**: Real-time API usage and cost monitoring
- **Dual Execution Modes**: Web UI (recommended) and CLI pipeline

## Architecture

### Pipeline Flow

```
Voice Agent Prompt → Script 1 (Claude) → Script 2 (Graphviz) → Script 3 (Path Analysis)
                         ↓                    ↓                      ↓
                      FSM JSON            Flowchart PNG         Clustered Paths
```

### Core Components

**Script 1: FSM Generation** (`script_1_gen.py`)
- Calls Claude Opus 4.5 with extended thinking to analyze system prompts
- Input: System instructions + voice agent prompt (separated by `---SEP---` in CLI mode)
- Output: `output.json` with vocabulary, states, intents, and transitions
- Pricing: $5/1M input tokens, $25/1M output tokens

**Script 2: Visualization** (`script_2_viz.py`)
- Converts FSM JSON into visual flowchart using Graphviz
- Output: `flowchart_claude.png` (rendered image) + `flowchart_claude` (DOT source)
- Validates transitions and filters null/missing required fields

**Script 3: Path Analysis** (`script_3_ana.py`)
- Analyzes all possible conversation paths from `STATE_GREETING` to `STATE_END_CONVERSATION`
- Clusters paths into P0 (archetypes), P1 (major variations), P2 (minor differences)
- Output: `clustered_flow_report.txt` + `clustered_flow_report.xlsx`
- Clustering thresholds: P2 (95% similarity), P1 (70% similarity)

### Service Layer Architecture

All services follow the same pattern: receive `FileManager` instance in constructor, provide session-isolated file operations.

**Core Services:**
- `FileManager` - Session-isolated file operations with `outputs/{session_id}/` directory management
- `SessionStateManager` - Centralized Streamlit session state (22 variables)
- `StreamingService` - FSM generation wrapper with session-based file saving
- `VisualizationService` - Flowchart generation with session-based output management
- `AnalysisService` - Path analysis wrapper with session-based reporting
- `ExcelService` - Excel export with vertical path layout and descriptions
- `ReportParser` - Text report → structured data for UI rendering
- `HistoryService` - Run history business logic with metadata management

## Prerequisites

- **Python 3.9 or higher**
- **Graphviz system library** (not just the Python package):
  - macOS: `brew install graphviz`
  - Ubuntu/Debian: `sudo apt-get install graphviz`
  - Windows: Download from [graphviz.org](https://graphviz.org/download/)
- **Anthropic API Key** with Claude Opus 4.5 access

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd QA_Eval

# Install Python dependencies
pip install -r requirements.txt

# Install Graphviz system library (macOS)
brew install graphviz

# Install Graphviz system library (Ubuntu/Debian)
sudo apt-get install graphviz
```

## Configuration

Create a `.env` file in the project root:

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

**SECURITY NOTE**: The `.env` file contains a live API key and should NEVER be committed to version control. It's already excluded in `.gitignore`.

## Usage

### Web UI (Recommended)

```bash
streamlit run app.py
# or
./run_app.sh
```

**Step-by-step Usage:**

1. **Field 1**: FSM extraction instructions (auto-populated from `prompt.txt`)
2. **Field 2**: Paste your voice agent system prompt
3. Click **"Generate Test Cases"** → Pipeline runs all 3 steps automatically
4. **View Results** in tabs:
   - **LLM Output**: Raw FSM JSON with vocabulary, states, and transitions
   - **Flowchart**: Visual graph of conversation flow
   - **Clustered Paths**: Organized conversation archetypes with variations
5. **Save to History** (optional): Click "Save to History" button, add notes, confirm
6. **View History**: Click "View Run History" in sidebar → Browse saved runs

**Available Downloads:**
- **LLM Output Tab**: Raw JSON
- **Flowchart Tab**: PNG image and DOT source
- **Clustered Paths Tab**: TXT (plain text) and XLSX (Excel spreadsheet)

### CLI Mode

```bash
# Run full pipeline
python master_pipeline.py

# Run individual scripts
python script_1_gen.py     # FSM generation only
python script_2_viz.py     # Visualization only
python script_3_ana.py     # Path analysis only
```

**Note**: CLI mode uses `prompt.txt` with `---SEP---` delimiter. Web UI uses split-field design.

## Example Output

### Sample FSM JSON

```json
{
  "vocabulary": {
    "user_intents": [
      "USER_GREETING",
      "USER_ASK_PRICE",
      "USER_CONFIRM_BOOKING",
      "USER_DECLINE_OFFER"
    ],
    "bot_states": [
      "STATE_GREETING",
      "STATE_COLLECTING_INFO",
      "STATE_CONFIRMING_DETAILS",
      "STATE_END_CONVERSATION"
    ],
    "tools": [
      "TOOL_BOOK_APPOINTMENT",
      "TOOL_CHECK_AVAILABILITY",
      "TOOL_SEND_CONFIRMATION"
    ]
  },
  "states": [
    {
      "state_name": "STATE_GREETING",
      "description": "Initial greeting and intent capture",
      "is_initial": true,
      "is_terminal": false
    }
  ],
  "transitions": [
    {
      "from_state": "STATE_GREETING",
      "to_state": "STATE_COLLECTING_INFO",
      "trigger_intent": "USER_GREETING",
      "action": "Greet user and ask for appointment details"
    }
  ]
}
```

### Flowchart Visualization

The pipeline generates visual flowcharts with:
- **Rounded nodes** representing states
- **Directed edges** showing transitions with intent labels
- **Top-to-bottom layout** for easy readability
- **Color-coded nodes** distinguishing initial, terminal, and intermediate states

### Path Analysis & Clustering

The path analysis identifies all possible conversation flows and groups them:

- **P0 (Archetypes)**: Core conversation patterns (e.g., "Happy Path", "Price Inquiry Flow")
- **P1 (Major Variations)**: Significant deviations from archetypes (70% similarity threshold)
- **P2 (Minor Differences)**: Small variations within P1 flows (95% similarity threshold)

Example clustering:
```
P0.1: Standard Booking Flow (85 paths)
  └─ P1.1: Early Price Inquiry (32 paths)
      └─ P2.1: Price + Availability Check (12 paths)
      └─ P2.2: Price Only (20 paths)
  └─ P1.2: Late Confirmation (53 paths)
```

## Project Structure

```
QA_Eval/
├── README.md                  # This file
├── CLAUDE.md                  # Detailed developer documentation
├── DEPLOYMENT.md              # Streamlit Cloud deployment guide
├── app.py                     # Streamlit web UI (main entry point)
├── master_pipeline.py         # CLI orchestrator
├── script_1_gen.py            # FSM generation (Claude API)
├── script_2_viz.py            # Flowchart visualization (Graphviz)
├── script_3_ana.py            # Path analysis and clustering
├── prompt.txt                 # FSM extraction instructions
├── requirements.txt           # Python dependencies
├── packages.txt               # System dependencies (for Streamlit Cloud)
├── .env                       # API key (DO NOT COMMIT)
├── .gitignore                 # Git exclusions
├── run_app.sh                 # Streamlit launcher script
├── utils/                     # Core utilities
│   ├── file_manager.py        # Session-isolated file operations
│   ├── session_state.py       # Streamlit session state management
│   └── history_manager.py     # Registry CRUD operations
├── services/                  # Business logic layer
│   ├── streaming_service.py   # FSM generation wrapper
│   ├── visualization_service.py # Flowchart generation wrapper
│   ├── analysis_service.py    # Path analysis wrapper
│   ├── excel_service.py       # Excel export with formatting
│   ├── report_parser.py       # Text report parsing
│   └── history_service.py     # Run history business logic
├── components/                # UI components
│   ├── execution_zone.py      # Thinking console display
│   ├── analysis_zone.py       # Metric cards + JSON viewer
│   ├── visual_zone.py         # Flowchart display
│   ├── results_zone.py        # Path analysis display
│   ├── top_navigation.py      # Sidebar navigation
│   ├── history_table.py       # Run history table
│   └── save_dialog.py         # Save run modal
├── outputs/                   # Session-scoped temporary outputs
│   └── {session_id}/          # Per-session output files
├── history/                   # Persistent run storage
│   ├── registry.json          # Run metadata registry
│   └── {session_id}/          # Saved run artifacts
└── static/                    # Static assets
```

## API Costs

The pipeline uses **Claude Opus 4.5** with the following pricing:
- **Input tokens**: $5 per 1M tokens
- **Output tokens**: $25 per 1M tokens
- **Extended thinking**: Enabled with 45k token budget

**Cost Tracking**: The UI displays real-time cost metrics after each run, including:
- Input token count and cost
- Output token count and cost
- Total cost in USD

**Monitoring**: Check usage in the [Anthropic Console](https://console.anthropic.com/) and set up usage alerts.

## Deployment

The application is ready for deployment to **Streamlit Community Cloud** with automatic GitHub integration.

**Quick Deploy:**
1. Push to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io/)
3. Add `ANTHROPIC_API_KEY` to Streamlit Secrets
4. Deploy! (auto-redeploys on every push)

**Important Notes:**
- Streamlit Cloud has ephemeral file storage (run history is temporary)
- Free tier: 1 CPU core, 800MB RAM, app sleeps after 7 days of inactivity
- See [`DEPLOYMENT.md`](DEPLOYMENT.md) for complete deployment guide

## Development

### Detailed Architecture

For comprehensive developer documentation, see [`CLAUDE.md`](CLAUDE.md) which covers:
- Service layer architecture and design patterns
- Session management and file operations
- UI component structure
- Error handling and validation
- Backward compatibility considerations

### Key Configuration Points

**Change Claude Model**
```python
# script_1_gen.py:28
model="claude-opus-4-5-20251101"  # Update model ID
```

**Adjust Clustering Sensitivity**
```python
# script_3_ana.py:72-74
THRESHOLD_P2_IDENTICAL = 0.95  # Higher = stricter P2 grouping (default: 0.95)
THRESHOLD_P1_VARIATION = 0.7   # Higher = stricter P1 grouping (default: 0.7)
```

**Change Start/End States**
```python
# script_3_ana.py:225-226
start_node = "STATE_GREETING"          # Entry point
end_node = "STATE_END_CONVERSATION"    # Terminal state
```

## Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'graphviz'"**
- Install the Graphviz system library (not just the Python package)
- macOS: `brew install graphviz`
- Ubuntu: `sudo apt-get install graphviz`

**"Invalid API key"**
- Verify `.env` file exists and contains `ANTHROPIC_API_KEY=your_key_here`
- Check for typos or extra spaces in the API key
- Ensure the key has access to Claude Opus 4.5

**"Excel export failed"**
- Non-fatal error - TXT download still available
- Check `excel_error` in session state for details
- Verify `pandas` and `openpyxl` are installed

**Flowchart rendering errors**
- Check that Graphviz system library is installed
- Verify transitions in `output.json` have valid `to_state` and `trigger_intent` fields
- Review `flowchart_source` DOT file for syntax errors

**Run history not persisting (Streamlit Cloud)**
- This is expected behavior - Streamlit Cloud has ephemeral storage
- Files in `history/` are wiped on app restart or redeployment
- For persistence, add cloud storage integration (S3/GCS)

## Contributing

Contributions are welcome! This project follows a service-oriented architecture with clear separation of concerns.

**Before contributing:**
- Read [`CLAUDE.md`](CLAUDE.md) for detailed architecture and design patterns
- Follow the existing service layer patterns (FileManager-based dependency injection)
- Add tests for new features
- Update documentation for API changes

**Development Workflow:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `streamlit run app.py`
5. Submit a pull request

## License

[Add your license information here]

## Acknowledgments

Built with:
- [Claude Opus 4.5](https://www.anthropic.com/claude) by Anthropic
- [Streamlit](https://streamlit.io/) for the web UI
- [Graphviz](https://graphviz.org/) for flowchart visualization
- [NetworkX](https://networkx.org/) for graph analysis

---

For questions or issues, please open a GitHub issue or refer to the detailed documentation in [`CLAUDE.md`](CLAUDE.md).
