FROM python:3.12 as base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install git for scrapers
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml /app/
COPY packages/backend /app/packages/backend
COPY packages/frontend /app/packages/frontend
COPY packages/mcp /app/packages/mcp
COPY scripts/setup_rag.py /app/scripts/
COPY scripts/document_scrapers/ /app/scripts/document_scrapers
COPY chroma_db /app/chroma_db

ENV UV_COMPILE_BYTECODE=1

WORKDIR /app

RUN uv sync --frozen --no-cache --no-install-workspace --no-dev

# Build RAG database during image build (only if not already present)
RUN if [ ! -f "/app/chroma_db/chroma.sqlite3" ]; then \
        uv run --no-sync /app/scripts/setup_rag.py; \
    fi
