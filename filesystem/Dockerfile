# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Install the MCP package.
WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir .

# Default entrypoint runs the MCP over stdio.
ENTRYPOINT ["better-mcps-filesystem"]
