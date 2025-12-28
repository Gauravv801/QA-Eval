# QA_Eval - Voice AI Agent FSM Extraction Pipeline

A pipeline that analyzes voice AI agent system prompts and extracts their conversation flow logic as Finite State Machines (FSMs). Uses Claude Opus 4.5's extended thinking capabilities to reverse-engineer system prompts into structured FSM representations with states, intents, and transitions.

## Overview

Transforms unstructured voice AI system prompts into actionable test cases by:

1. **Analyzing** system prompts using Claude Opus 4.5 with extended thinking
2. **Extracting** structured FSM representations (vocabulary, states, intents, transitions)
3. **Visualizing** conversation flows as interactive flowcharts
4. **Analyzing** all possible conversation paths and clustering them into archetypes

**Use Cases:**
- QA testing for voice AI agents
- Conversation flow analysis and optimization
- System prompt validation and debugging

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

## Acknowledgments

Built with:
- [Claude Opus 4.5](https://www.anthropic.com/claude) by Anthropic
- [Streamlit](https://streamlit.io/) for the web UI
- [Graphviz](https://graphviz.org/) for flowchart visualization
- [NetworkX](https://networkx.org/) for graph analysis

---

For questions or issues, please open a GitHub issue or refer to the detailed documentation in [`CLAUDE.md`](CLAUDE.md).
