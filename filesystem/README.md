# Better MCP: `filesystem`

A safe, root-scoped filesystem MCP.

Part of the [`better-mcps`](https://github.com/aron98/better-mcps) monorepo.

## Security model

- The server is started with **one or more allowed root directories**.
- Tools require **absolute paths**.
- All paths are resolved (including symlinks) and must be **under one of the allowed roots**.
- If no roots are provided, the server exits (no implicit default like `cwd`).

## Run (STDIO)

```bash
# Recommended (no clone): run from PyPI via uvx
uvx better-mcps-filesystem /absolute/allowed/root1 /absolute/allowed/root2

# Alternatively, if you installed locally:
better-mcps-filesystem /absolute/allowed/root1 /absolute/allowed/root2

# Or (module entrypoint):
python -m better_mcps_filesystem /absolute/allowed/root1 /absolute/allowed/root2
```

## Claude Desktop example

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "uvx",
      "args": [
        "better-mcps-filesystem",
        "/absolute/allowed/root1",
        "/absolute/allowed/root2"
      ]
    }
  }
}
```

## Docker example

When running this MCP in Docker, the server can only access paths *inside the container*.
So you must **mount** any directories you want this MCP to be able to access (read/list today; edit/write if you add write tools later).

### Run

You must **mount** the directories you want this MCP to access, and pass the *container paths* as the allowed roots.

```bash
docker run --rm -i \
  -v "/Users/erdelyia/Projects/project:/roots/project:rw" \
  -v "/Users/erdelyia/Projects/project2:/roots/project2:rw" \
  ghcr.io/aron98/better-mcps-filesystem:latest \
  /roots/project /roots/project2
```

Alternatively, you can build the image yourself from `filesystem/Dockerfile`.

Notes:
- `-i` keeps STDIN open (needed for MCP over stdio).
- Use `:rw` if you expect the MCP to modify files; use `:ro` to force read-only.

## VS Code example

VS Code supports variable substitution for the current workspace folder (your *workdir*).
You can use that as the allowed root so the MCP is automatically scoped to the open workspace.

Example (conceptually):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "uvx",
      "args": ["better-mcps-filesystem", "${workspaceFolder}"]
    }
  }
}
```

If you use a multi-root workspace, VS Code can target a specific folder (e.g. `${workspaceFolder:my-folder}`).

## API

### Tools

- `list_dir(params: object) -> str | dict`
  - **Params object** (Pydantic-validated):
    - `path` (string, required): absolute directory path under an allowed root
    - `max` (int, default `200`, max `2000`)
    - `format` ("text"|"json", default `"text"`)
    - `detailed` (bool, default `false`): include `mode` (permissions) and `size`
  - Includes hidden files; sorted by name
  - If output is truncated, a hint is included (text mode appends a line; json mode includes `truncated/total/shown`)

- `read_text_file(params: object) -> str`
  - **Params object**:
    - `path` (string, required): absolute file path under an allowed root
  - file is read as UTF-8

### Resources

- `resource://roots` — returns `list[str]` of allowed root directories
