# MCP: `filesystem`

A safe, root-scoped filesystem MCP.

## Security model

- The server is started with **one or more allowed root directories**.
- Tools require **absolute paths**.
- All paths are resolved (including symlinks) and must be **under one of the allowed roots**.
- If no roots are provided, the server exits (no implicit default like `cwd`).

## Run (STDIO)

```bash
# Console script
filesystem /absolute/allowed/root1 /absolute/allowed/root2

# Module entrypoint
python -m filesystem /absolute/allowed/root1 /absolute/allowed/root2
```

## Claude Desktop example

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

## API

### Tools

- `list_dir(path: str) -> list[str]`
  - `path` must be an **absolute directory path** under an allowed root

- `read_text_file(path: str) -> str`
  - `path` must be an **absolute file path** under an allowed root
  - file is read as UTF-8

### Resources

- `resource://roots` — returns `list[str]` of allowed root directories
