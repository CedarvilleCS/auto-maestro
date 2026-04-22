ARG BASE_IMAGE=localhost/automaestro/base:latest

FROM ${BASE_IMAGE}

COPY . /app

WORKDIR /app

RUN uv sync --frozen --no-cache --package mcp

EXPOSE 5000

CMD ["uv", "run", "--no-sync", "fastapi", "dev", "packages/mcp/src/mcp/main.py", "--port", "5000", "--host", "0.0.0.0"]

