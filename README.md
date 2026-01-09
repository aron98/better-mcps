# better-mcps

A collection of small, well-written **FastMCP (MCP 2.0)** servers that do simple things well.

## Install

Using `pip`:

```bash
python -m pip install -e .
```

Or with `uv`:

```bash
uv pip install -e .
```

## Included MCP servers

- [`filesystem`](src/filesystem/README.md) — safe, root-scoped filesystem tools (absolute paths only)

## Run an MCP (STDIO)

Each MCP in this repo runs over **STDIO** by default.

After installing, run the MCP via its console script (preferred) or module entrypoint.

Example:

```bash
filesystem /absolute/allowed/root1 /absolute/allowed/root2
# or:
python -m filesystem /absolute/allowed/root1 /absolute/allowed/root2
```

## Adding a new MCP

Convention:

- Add a new package at `src/<name>/`
- Implement the server in `src/<name>/server.py` with a `main()`
- Provide `src/<name>/__main__.py` so it can run as a module
- Add a console script in `pyproject.toml` under `[project.scripts]`
- Add `src/<name>/README.md` and link it from this root README
