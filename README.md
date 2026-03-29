# MCP Weather App (local agent)

Sample project: a **FastMCP** weather server (tools backed by [wttr.in](https://wttr.in)), a **stdio** MCP subprocess, and a **LangChain** agent via **mcp-use** with **Ollama** (`langchain-ollama`).

**Rendered HTML (diagrams, styling):** The long-form doc is published at **[https://georgejinu-labs.github.io/mcp-weather-app-local-agent/](https://georgejinu-labs.github.io/mcp-weather-app-local-agent/)** — built from [`docs/index.html`](docs/index.html). On GitHub’s file browser, `docs/index.html` opens as **raw source**; use the Pages URL above for a normal web page.

- **First-time setup:** **Settings → Pages →** Source: branch `main`, folder **`/docs`**, Save (wait ~1 minute for the site to update after pushes).
- **Edit the doc:** change [`docs/index.html`](docs/index.html) in the repo, commit, push.
- **Offline:** open `docs/index.html` from a local clone in your browser (double-click or drag into a window).

---

## Components involved

These are the pieces you see wired together in a trace such as `execution.log` (from `WEATHER_AGENT_TRACE=1`):


| Component                                 | Role                                                                                                                                    |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `**agentic_client.py`**                   | Async entrypoint: builds MCP config, `ChatOllama`, `MCPAgent`, runs queries.                                                            |
| `**mcp-use` (`MCPClient`)**               | Spawns the server, holds **stdio** sessions, sends MCP JSON-RPC (`initialize`, `tools/list`, `tools/call`, …).                          |
| `**mcp-use` (`MCPAgent`)**                | Loads tools via MCP, wraps them as **LangChain** tools, runs `**create_agent`** → **LangGraph** loop, optional **conversation memory**. |
| `**mcp` (Python SDK)**                    | Client side of the MCP protocol over stdin/stdout to the child process.                                                                 |
| **Child process: `uv run src/server.py`** | Isolated env; runs the MCP **server** entrypoint.                                                                                       |
| `**server.py` + FastMCP**                 | Declares MCP tools (`get_weather`, `get_forecast`); stdio transport for subprocess hosting.                                             |
| `**tools/weather.py`**                    | Implements HTTP calls to wttr.in; returns text to the MCP tool handler.                                                                 |
| **LangGraph**                             | Agent graph: middleware → **model** → (optional) **tools** → model again until no tool calls.                                           |
| `**ModelCallLimitMiddleware`**            | Caps model turns (maps to `max_steps` in mcp-use).                                                                                      |
| `**ChatOllama` (`langchain_ollama`)**     | Chat model binding; calls **Ollama** over HTTP (e.g. `http://localhost:11434`).                                                         |
| **Ollama**                                | Hosts the local LLM (e.g. `qwen3.5:9b`).                                                                                                |
| **LangChain callbacks**                   | With trace on: `StdOutCallbackHandler` prints `[chain/*]`, `[llm/*]`, `[tool/*]` lines.                                                 |
| **httpx**                                 | Used by Ollama client and weather fetches.                                                                                              |


---

## Execution flow (from trace logs)

The log sequence is: **connect MCP → discover tools → build agent → for each user message, run the graph** (model ↔ tools ↔ MCP until the model answers without tools).

**Viewing diagrams:** Fenced blocks marked `mermaid` render as graphics on **github.com** (and in editors with a Mermaid preview). In plain Markdown previews they often look like an unreadable code block — use the **ASCII** diagrams in that case, see the [rendered HTML doc](https://georgejinu-labs.github.io/mcp-weather-app-local-agent/), open [docs/index.html](docs/index.html) locally, or paste the Mermaid source into [mermaid.live](https://mermaid.live).

### High-level ASCII

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Client process (agentic_client.py)                                          │
│                                                                              │
│  MCPAgent.initialize()                                                       │
│    │                                                                         │
│    ├─► MCPClient spawns:  uv run src/server.py                               │
│    │         │                                                               │
│    │         └─► stdio JSON-RPC:  initialize → tools/list → (resources,      │
│    │              prompts)                                                   │
│    │                                                                         │
│    ├─► LangChainAdapter: MCP tools → BaseTool (get_weather, get_forecast)    │
│    └─► create_agent(...) → LangGraph + ModelCallLimitMiddleware              │
│                                                                              │
│  MCPAgent.run("...")                                                         │
│    │                                                                         │
│    ├─► messages = [memory...] + HumanMessage                                 │
│    └─► LangGraph astream (loop):                                             │
│           ModelCallLimitMiddleware.before_model                              │
│           → model (ChatOllama → Ollama)  "System + tools + Human + ..."      │
│           → ModelCallLimitMiddleware.after_model                             │
│           → if tool_calls:                                                   │
│                 tools node → MCP tools/call → FastMCP → weather.py → wttr.in │
│                 → ToolMessage                                                │
│                 → back to model (now prompt includes tool result)            │
│           → repeat until AIMessage has no tool_calls                         │
│           → final text to user; optional memory update                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

```
                    ┌──────────────────────────────────────┐
                    │         Client process               │
  MCPAgent.init ──► │  MCPClient (stdio)                   │
        │           │       │                              │
        │           │       ▼                              │
        │           │  LangChainAdapter                    │
        │           │       │                              │
        │           │       ▼                              │
        └──────────►│  LangGraph (create_agent)            │
  MCPAgent.run ───► │       │                              │
                    │   model node ──────► ChatOllama ─────┼──► Ollama
                    │       │                    ▲         │
                    │       │ tool_calls         │         │
                    │       ▼                    │         │
                    │  tools node ───────────────┘         │
                    │       │                              │
                    └───────┼──────────────────────────────┘
                            │ tools/call (stdio)
                            ▼
                    ┌───────────────────┐      HTTP
                    │ FastMCP (child)   │ ─────────────► wttr.in
                    │  weather.py       │
                    └───────────────────┘
```

### What the log lines map to

1. `**Connecting to MCP implementation: uv**` — stdio connector starting the child.
2. `**stdio:uv run src/server.py -> initialize**` (then `<- initialize`) — MCP handshake; server is ready.
3. `**-> tools/list**` — discover `get_weather` / `get_forecast`.
4. `**Created 2 LangChain tools from client**` — adapter finished; agent can call them.
5. `**💬 Received query**` / `**🏁 Starting agent execution**` — one `run()` begins.
6. `**Entering new LangGraph chain**` — graph run with `messages` (history + new user text).
7. `**llm:ChatOllama` … `prompts`: System + tool list + Human** — **context injection** for that turn (second model call also includes AI/Tool lines from the same turn).
8. `**tool:get_weather` / `tools/call`** — LangChain tool execution forwarded to MCP; server runs Python handler and wttr.in.
9. `**✅ Agent finished with output**` — model returned text without further tool calls.
10. **Second user question** — log shows **longer** `messages` / prompts: prior Human, AI, Tool, AI turns are prepended (**memory**).

---

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/) with your chosen model pulled, run from the **repository root**.

```powershell
uv sync
# Ollama running, e.g. ollama serve
uv run python src/client/agentic_client_simple.py
```

Verbose trace (matches the style of `execution.log`):

```powershell
$env:WEATHER_AGENT_TRACE=1
uv run python src/client/agentic_client.py
```

Tests:

```powershell
uv run pytest
```

---

## Reference log

An example captured run is in `[execution.log](execution.log)` (initialize → first query with `get_weather` → second query with multi-tool pattern). Timings in that file reflect local machine and cold model load.