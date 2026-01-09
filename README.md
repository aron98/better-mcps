# better-mcps

A monorepo of small, well-written **FastMCP (MCP 2.0)** servers.

## MCP packages

- [`better-mcps-filesystem`](filesystem/README.md)

## Development

Each MCP is a self-contained Python package living in a top-level directory (e.g. `filesystem/`).

### Run locally

```bash
cd filesystem
python -m pip install -e .
better-mcps-filesystem /absolute/allowed/root1 /absolute/allowed/root2
```
