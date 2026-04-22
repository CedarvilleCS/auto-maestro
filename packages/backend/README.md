# Backend (FastAPI + LangGraph)

The backend is the orchestration core of AutoMaestro.
It coordinates agent routing, state transitions, confidence scoring, sandbox execution requests, and frontend communication. Built on FastAPI and LangGraph, it enforces the structural constraints that support AutoMaestro’s reliability-first design.

---

## Architectural Role

The backend serves as the central control layer between:
- The Frontend (NiceGUI UI)
- The Agent Orchestration Graph
- The MCP Server (sandbox execution layer)
- The RAG databases (ChromaDB + DocumentDB)

It is responsible for:
- Supervising agent transitions
- Maintaining structured system state
- Logging confidence scores
- Routing execution requests through MCP
- Normalizing sandbox outputs before reintegration
- Managing API endpoints and WebSocket connections

This component implements the coordination logic behind AutoMaestro’s three reliability pillars.

---

## Core Responsibilities

### 1️⃣ Agent Orchestration
- Supervisor-agent routing
- Tool-specific agent invocation
- Context management via LangGraph state objects

### 2️⃣ Confidence Scoring
- Captures and logs model-derived confidence values
- Persists scores across agent transitions
- Surfaces metadata to frontend

### 3️⃣ Sandbox Execution Mediation
- Forwards commands to the MCP server
- Receives and normalizes structured execution output
- Prevents direct execution outside sandbox boundaries

### 4️⃣ API & Real-Time Communication
- REST endpoints for chat and orchestration
- WebSocket endpoint for terminal streaming
- Server-Sent Events (SSE) for live agent transition updates

---

## Structure
```
packages/backend/
├── src/
│   ├── main.py        # FastAPI application entry point
│   ├── api/           # REST and WebSocket route definitions
│   ├── services/      # Business logic and orchestration logic
│   ├── models/        # Pydantic schemas and state models
│   └── tests/         # Unit and integration tests
└── requirements.txt
```
## Quick Start

From project root
cd packages/backend
uv run --env-file ../../.env -- fastapi dev src/main.py

## Testing

cd packages/backend
pytest

## Development Notes
- Formatting and linting are managed via pre-commit hooks.
- The backend is ASGI-compatible and supports concurrent endpoint execution.
- All sandbox execution must pass through the MCP service; no direct container interaction should occur here.

## Security & Scope
The backend:
- Does not directly execute system-level commands
- Does not expose host-level infrastructure
- Assumes sandbox isolation is enforced via MCP
- Is intended for controlled lab environments
Production deployment would require additional authentication, rate limiting, and endpoint hardening.

---

## Agent Types

The backend orchestrates three categories of agents:

- **Supervisor Agent (Router)**: Interprets user intent, selects the appropriate specialist agent, maintains structured state transitions, preserves relevant context while discarding noise. Does not generate tool commands directly.

- **Tool Specialist Agents**: Each cybersecurity tool has a dedicated agent (Nmap, Hydra, Hashcat, Metasploit, SSH, Telnet, PsExec). These agents generate structured commands only, use tool-scoped RAG retrieval, and operate within tightly engineered system prompts.

- **General Chat Agent**: Fallback for off-topic requests, unsupported tool usage, or ambiguous queries. Ensures safe degradation instead of hallucinated tool execution.

---

## Creating a New Agent

To add a new tool-specific agent, modify `packages/backend/src/backend/ai_graph.py`:

1. Add the tool name to the `tool_names` list (line ~735)
2. Add a help command to `TOOL_HELP_COMMANDS` (line ~39)
3. Optionally add a RAG database for the tool via `scripts/setup_rag.py`

The graph automatically creates two nodes per tool:
- **Tool node** (e.g., `nmap`): Uses `tool_rag_database` + `prompt_user` to generate commands
- **Tool handler** (e.g., `nmap_handler`): Executes via MCP and routes to response_agent

The Supervisor routes to tool names defined in `Router.next` (line ~678).

---

## Agent Execution Model

All agents generate commands but do not execute them directly. The backend mediates execution through MCP:
1. Agent generates structured command → Backend validates and forwards to MCP → MCP executes in sandbox → Output returned to agent for context continuation

---

## Testing Agent Integration

Agent reliability is evaluated through:
- Routing accuracy tests (correct agent selected)
- Command syntax validation
- Semantic consistency across repeated runs
- Graceful degradation testing

All new agents should include tests validating proper routing, valid command generation, and safe fallback behavior.

---

## Related READMEs

[MAIN](../../README.md)

[Frontend](../frontend/README.md)
