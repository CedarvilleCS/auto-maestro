# AutoMaestro

AutoMaestro is a semi-autonomous offensive cybersecurity AI assistant focused on improving reliability and consistency during extended AI-assisted operations.
Rather than pursuing unrestricted autonomy, AutoMaestro emphasizes architectural safeguards that raise the safe autonomy threshold for entry-level cyber operators.

The system integrates:

- Real-time confidence scoring
- Sandbox-constrained execution
- Focused multi-agent orchestration
- Retrieval-Augmented Generation (RAG) for tool grounding

AutoMaestro was developed as part of senior design research exploring how architectural constraint—not model size alone—can improve reliability in long-running autonomous workflows.

> AutoMaestro is a research prototype designed for controlled lab environments.  
> It is not intended for deployment against live infrastructure.

## Table of Contents
- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Development](#development)
- [Formatting](#formatting)
- [Running the Backend](#running-the-backend)
- [Running the Frontend](#running-the-frontend)
- [VSCode](#vscode)
- [API Documentation](#api-documentation)
- [RAG System Setup](#rag-system-setup)
- [Module READMEs](#module-readmes)
- [License](#license)

## Problem Statement

Large Language Models (LLMs) demonstrate strong reasoning capabilities but degrade in reliability during extended, multi-step operations. In offensive cyber contexts, even minor hallucinations or tool misuse can lead to mission failure or unintended consequences.

Key challenges include:

- Non-deterministic outputs
- Context window degradation (“context rot”)
- Hallucinated commands
- Tool misuse during prolonged reasoning

AutoMaestro addresses these challenges through three coordinated architectural controls:

1. **Confidence-Aware Reasoning** – Exposes model uncertainty to reduce blind trust.
2. **Sandbox-Constrained Execution** – Validates all commands in an isolated SEED Lab environment.
3. **Multi-Agent Specialization** – Restricts each agent to a single tool to minimize cross-tool reasoning drift.

---
## Research Paper
See AutoMaestro Paper.docx for full methodology, evaluation, and architectural analysis.

## System Architecture

AutoMaestro is implemented as a multi-layered architecture:

- **Frontend (NiceGUI)**  
  Provides chat interaction, terminal visibility, and agent transition logging.

- **Backend (FastAPI + LangGraph)**  
  Manages agent routing, state transitions, confidence logging, and execution control.

- **Agent Layer (LangChain + LangGraph)**  
  Supervisor-worker model with:
  - Tool specialist agents (Nmap, Hydra, Hashcat, Metasploit, SSH, Telnet, PsExec)
  - General chat fallback agent

- **RAG System (ChromaDB)**  
  Tool-specific documentation grounding to reduce hallucinations.

- **Sandbox Environment (SEED Lab + MCP Server)**  
  All generated commands are routed through a Model Context Protocol (MCP) server and executed inside an isolated lab network.

This layered separation ensures reasoning, execution, and validation remain bounded and observable.

---
## Repository Structure

```
/
├─ data/ # Tool datasets and vulnerability templates
├─ packages/
│ ├─ backend/ # FastAPI agent orchestration service
│ ├─ frontend/ # NiceGUI frontend
│ └─ mcp/ # MCP / coordination layer
├─ sandbox_setup/ # SEED Lab + Docker environment
├─ scripts/ # Utility and setup scripts
├─ AGENTS.md # Agent documentation
├─ docker-compose.yml
├─ Dockerfile # Base image setup for faster reloads after first build
└─ README.md
```

## Quick Start (VM or Local)

1. Copy and rename the `.env.example` to `.env`.
2. Open `.env` in a text editor
3. Assign your groq API key to `GROQ_API_KEY`
4. Set up the RAG system (see [RAG System Setup](#rag-system-setup))
5. Start the full environment: `./scripts/up.sh`
6. Stop all containers: `./scripts/down.sh`

## Configuration

Configuration is managed via environment variables. Copy `.env.dev.example` to `.env.dev` for local development.

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GROQ_API_KEY` | API key for Groq LLM provider | Yes* | - |
| `LLM_PROVIDER` | LLM provider (`openai_compatible`) | Yes* | - |
| `LLM_API_BASE` | OpenRouter or compatible API base URL | If using OpenRouter | - |
| `LLM_API_KEY` | API key for OpenRouter | If using OpenRouter | - |
| `LLM_MODEL` | Model identifier for LLM | No | - |
| `DEBUG` | Enable debug logging | No | `false` |
| `BASE_IMAGE` | Docker base image | No | - |
| `FRONTEND_HOST` | Frontend bind address | No | `127.0.0.1` |
| `FRONTEND_PORT` | Frontend port | No | `3030` |
| `BACKEND_HOST` | Backend bind address | No | `127.0.0.1` |
| `BACKEND_PORT` | Backend port | No | `3000` |
| `MCP_HOST` | MCP server bind address | No | `127.0.0.1` |
| `MCP_PORT` | MCP server port | No | `5000` |
| `DATABASE_HOST` | MongoDB host | No | `127.0.0.1` |
| `DATABASE_PORT` | MongoDB port | No | `10260` |
| `DATABASE_NAME` | MongoDB database name | No | `main` |
| `DATABASE_USER` | MongoDB username | No | `user` |
| `DATABASE_PASS` | MongoDB password | No | `password` |
| `DATABASE_URL` | Full MongoDB connection URL | No | Auto-built |
| `DATABASE_INSECURE_TLS` | Allow insecure TLS for MongoDB | No | `true` |
| `AUTO_EXECUTE_COMMANDS` | Execute generated commands automatically | No | `true` |
| `DEFAULT_EXECUTOR_CONTAINER` | Default container for command execution | No | `A-10.8.0.99` |

*Either `GROQ_API_KEY` or (`LLM_PROVIDER` + `LLM_API_KEY`) is required.

### Configuration Files

- `.env` – Production environment (used in Docker)
- `.env.dev` – Development environment (local development)

## Development
The below instructions are for developing AutoMaestro. Follow the above quick-start guide for setting it up for typical use.

To develop AutoMaestro:
1. Download `uv` from https://docs.astral.sh/uv/getting-started/installation/.
2. Run `uv sync --frozen`. `uv` will handle the virtual environment itself, so no need to run the `activate` script.
3. Here, you have two options:
    - If running directly on your local machine, copy and rename the `.env.dev.example` to `.env.dev`.
    - If running this under docker, copy and rename the `.env.example` to `.env`.
4. Open the new environment file and assign the `GROQ_API_KEY` to a valid [groq token](https://console.groq.com/keys).
    - Alternatively, setup OpenRouter, as seen in the example environment files.
5. Optional: Run `uv run pre-commit install` to setup formatting automation. This is only recommended if you want forced formatting for every commit, which is more useful for code agents than humans.

### Formatting
If you installed the pre-commit hook, then you will automatically have the formatter apply when you run `git commit`. If it is able to format a file, the run will fail and the stage will not be committed. You must add the changes from the formatter to the stage, e.g. `git add .`, then commit again. As long as there were no other errors, this should succeed on the second run.

### Running the backend individually
Use `uv run --env-file .env.dev -- fastapi dev packages/backend/src/backend/main.py --port 3000` to start up a dev environment without the debugger. The URL to navigate to will be output in the console. To test the API, you can open the SwaggerUI by navigating to `http://<host>:<port>/docs`.

### Running the frontend individually
Use `uv run --env-file .env.dev -- py packages/frontend/src/frontend/main.py` to start up the frontend. The URL to navigate to will be output in the console and it may open the browser automatically.

### Docker
There is the ability to either use a local built base image or a pulled image from the upstream GitHub package. This can be overridden with the `BASE_IMAGE` environment variable in the `.env` files.

### VSCode
If you are using VSCode, there is also a launch configuration for debugging.

## API Documentation

The backend exposes a REST API at `/api/v1/`. Swagger documentation is available at `/api/v1/docs` when the backend is running.

### Endpoints

#### Actors
- `GET /api/v1/actors` – List actors
- `POST /api/v1/actors` – Create actor
- `GET /api/v1/actors/{actor_id}` – Get actor
- `PATCH /api/v1/actors/{actor_id}` – Update actor
- `DELETE /api/v1/actors/{actor_id}` – Delete actor

#### Conversations
- `GET /api/v1/conversations` – List conversations
- `POST /api/v1/conversations` – Create conversation
- `GET /api/v1/conversations/{conversation_id}` – Get conversation
- `PATCH /api/v1/conversations/{conversation_id}` – Update conversation
- `DELETE /api/v1/conversations/{conversation_id}` – Delete conversation
- `POST /api/v1/conversations/{conversation_id}/messages` – Send message
- `POST /api/v1/conversations/resume` – Resume last conversation

## RAG System Setup

The RAG system provides documentation context for security tools used by the agents. This unified script handles both documentation scraping and RAG database building.

**Docker Users:** When building the Docker image, the complete RAG database will be automatically generated during the build process. If you've already created a partial database locally (in `./chroma_db`), it will be copied into the image and preserved instead.

### Available Tools
- **nmap**: Network scanning and discovery
- **metasploit**: Penetration testing framework
- **hydra**: Password cracking
- **hashcat**: Password recovery
- **ssh**: OpenSSH documentation
- **telnet**: Telnet protocol
- **psexec**: Remote execution

### Setup Commands

**Complete setup (scrape documentation + build RAG database):**
```bash
uv run python scripts/setup_rag.py
```

**Set up specific tools only:**
```bash
uv run python scripts/setup_rag.py --tools nmap,metasploit
```

**Force rebuild of RAG database:**
```bash
uv run python scripts/setup_rag.py --rebuild
```

**Force re-scrape documentation:**
```bash
uv run python scripts/setup_rag.py --force-scrape
```

**Scrape documentation only (no RAG build):**
```bash
uv run python scripts/setup_rag.py --scrape-only
```

**List available tools:**
```bash
uv run python scripts/setup_rag.py --list
```

## Module READMEs

[MCP](./packages/mcp/README.md)

[Frontend](./packages/frontend/README.md)

[Backend](./packages/backend/README.md)

[Scripts](./scripts/README.md)

[Sandbox](./sandbox_setup/README.md)

## License

MIT License – see LICENSE file for details.

## Authors
Elijah Lewis

Gavin Montgomery

Anthony Ruffolo


