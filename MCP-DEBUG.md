# Built-in MCP debug server

These builds include Lichii's opt-in debug server and its MCP adapter. It is off
unless `EDEN_NX2_DEBUG_SERVER` is set, so normal play is unaffected.

## Start the server

Set the address in `nx2_switches.txt` or in the environment before launching:

```text
EDEN_NX2_DEBUG_SERVER=127.0.0.1:6545
```

Optional: move dumps elsewhere.

```text
EDEN_NX2_DEBUG_DIR=<dir>
```

The log shows:

```text
Debug server listening on 127.0.0.1:6545, dump dir ...
```

## Adapter

`tools/nx2/debug_mcp.py` is a stdlib-only Python adapter. Without `--call` it is
a stdio MCP server for an MCP client. With `--call` it runs one request:

```bash
python tools/nx2/debug_mcp.py --server 127.0.0.1:6545 --call "{\"method\":\"status\"}"
python tools/nx2/debug_mcp.py --server 127.0.0.1:6545 --call "{\"method\":\"screenshot\",\"params\":{\"height\":1080}}" --out shot.png
python tools/nx2/debug_mcp.py --server 127.0.0.1:6545 --call "{\"method\":\"log_tail\",\"params\":{\"lines\":200}}"
```

Request format: `{"method": <tool>, "params": {...}}`.

## Tools

- `status`
- `screenshot`
- `log_tail`, `log_filter`
- `capture_frame` — pass colour targets, dispatch storage images, present source
- `capture_image`
- `reject_shaders` — `EDEN_NX2_REJECT_HASH` at runtime; `"reject": false` restores
- `read_memory`, `search_memory`, `read_gpu_memory`
- `input`, `input_sequence`
- `sample` — sampled thread stacks

`read_memory` and `search_memory` read guest virtual memory; `read_gpu_memory`
reads GPU virtual memory. `capture_frame`, `reject_shaders` and
`read_gpu_memory` are Vulkan-only.

Shader hashes are 16 hex digits. A shorter hash is refused, not zero-padded.

## Safety

The server listens on loopback only. It is intended for local debugging. Do not
expose the port to a network. Dumps and captures can contain game assets; keep
them local and do not upload `.rdc` captures or dumps publicly.
