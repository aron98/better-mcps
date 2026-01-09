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

---

## MCP: `filesystem`

A safe, root-scoped filesystem MCP.

### Run locally (STDIO transport)

FastMCP defaults to **STDIO** when you call `run()`.

This server **requires** you to pass one or more *absolute* allowed root directories on the command line.

```bash
# Option 1: module entrypoint
python -m filesystem /absolute/allowed/root1 /absolute/allowed/root2

# Option 2: console script
filesystem /absolute/allowed/root1 /absolute/allowed/root2
```

### Claude Desktop example

In your Claude Desktop MCP config, point at the installed entrypoint and pass the allowed roots as arguments.

Example (adjust paths as needed):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": [
        "-m",
        "filesystem",
        "/absolute/allowed/root1",
        "/absolute/allowed/root2"
      ]
    }
  }
}
```

### Provided tools/resources

#### Tools
- `list_dir(path: str) -> list[str]` (absolute path required)
- `read_text_file(path: str) -> str` (absolute path required)

#### Resources
- `resource://roots` (list allowed roots)
