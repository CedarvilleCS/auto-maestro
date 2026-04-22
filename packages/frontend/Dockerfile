ARG BASE_IMAGE=localhost/automaestro/base:latest
ARG FRONTEND_PORT

FROM ${BASE_IMAGE}

ENV FRONTEND_PORT=$FRONTEND_PORT

COPY . /app

WORKDIR /app
RUN uv sync --frozen --no-cache --package frontend

EXPOSE $FRONTEND_PORT

CMD uv run --no-sync packages/frontend/src/frontend/main.py
