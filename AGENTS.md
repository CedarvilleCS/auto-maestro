# AGENTS.md

## Commands

```bash
# Install dependencies
uv sync --frozen

# Lint (uses ruff, not black)
uv run ruff check packages/

# Run backend (port 3000)
uv run --env-file .env.dev -- fastapi dev packages/backend/src/backend/main.py --port 3000

# Run frontend (port 3030)
uv run --env-file .env.dev -- py packages/frontend/src/frontend/main.py

# Run tests
uv run pytest

# Setup RAG system
uv run python scripts/setup_rag.py [--tools nmap,metasploit] [--rebuild]
```

## Environment Setup

1. Copy `.env.dev.example` → `.env.dev`
2. Set either `GROQ_API_KEY` or OpenRouter vars (`LLM_PROVIDER=openai_compatible`, `LLM_API_KEY`, `LLM_API_BASE`)
3. Pre-commit: `uv run pre-commit install`

## Architecture

- **Workspace**: Python monorepo with 3 packages (`packages/{backend,frontend,mcp}`)
- **Backend**: FastAPI + LangGraph orchestration (port 3000)
- **Frontend**: NiceGUI 3.2.0 (port 3030)
- **Linting**: Ruff (not black/formatter)

## Key References

- Full dev instructions: `README.md`
- Package READMEs: `packages/*/README.md`