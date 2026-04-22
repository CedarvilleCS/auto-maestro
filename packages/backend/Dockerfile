ARG BASE_IMAGE=localhost/automaestro/base:latest
ARG BACKEND_PORT
ARG FASTAPI_RUN_MODE

FROM ${BASE_IMAGE}

ENV BACKEND_PORT=$BACKEND_PORT
ENV FASTAPI_RUN_MODE=$FASTAPI_RUN_MODE

COPY . /app

WORKDIR /app
RUN uv sync --frozen --no-cache --package backend

EXPOSE $BACKEND_PORT

CMD ["uv", "run", "--no-sync", "fastapi", "dev", "packages/backend/src/backend/main.py", "--port", "3000", "--host", "0.0.0.0"]
