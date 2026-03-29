"""
Weather MCP + LangChain/Ollama client.

Trace pipeline (MCP stdio, tool calls, LLM, memory/context):
  PowerShell:  $env:WEATHER_AGENT_TRACE=1; uv run python src/client/agentic_client.py
  Or set MCP_USE_DEBUG=2 (mcp-use default: INFO-style logs without LangChain internals).

What you see when WEATHER_AGENT_TRACE=1:
  - mcp_use: session init, tools discovered, each query, graph node DEBUG lines
  - LangChain: set_debug(True) + create_agent(debug=True) → graph execution details
  - StdOutCallbackHandler: LLM / chain start-end and tool events on stdout
  - After each run: system prompt + conversation history (what gets injected next turn)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys


def _trace_enabled() -> bool:
    return os.environ.get("WEATHER_AGENT_TRACE", "").strip().lower() in ("1", "true", "yes")


def _configure_trace_logging() -> bool:
    """Return True if trace mode is on. Must run before `from mcp_use import MCPAgent`."""
    if not _trace_enabled():
        return False
    from mcp_use.logging import Logger

    Logger.set_debug(2)
    Logger.configure(level=logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("mcp").setLevel(logging.DEBUG)
    return True


_TRACE = _configure_trace_logging()

from langchain_ollama import ChatOllama
from mcp_use import MCPAgent, MCPClient


def _print_injected_context(agent: MCPAgent, title: str) -> None:
    """Show system prompt and memory the next LLM call will build from."""
    sys_msg = agent.get_system_message()
    print(f"\n--- {title} ---", file=sys.stderr)
    if sys_msg:
        preview = sys_msg.content
        if isinstance(preview, str) and len(preview) > 2000:
            preview = preview[:2000] + "\n... [truncated]"
        print(f"System message:\n{preview}", file=sys.stderr)
    hist = agent.get_conversation_history()
    print(f"Conversation history: {len(hist)} message(s)", file=sys.stderr)
    for i, msg in enumerate(hist):
        t = type(msg).__name__
        c = getattr(msg, "content", "")
        if isinstance(c, str) and len(c) > 500:
            c = c[:500] + "... [truncated]"
        print(f"  [{i}] {t}: {c!r}", file=sys.stderr)


async def run_memory_chat():
    config = {
        "mcpServers": {
            "weather": {
                "command": "uv",
                "args": [
                    "run",
                    "src/server.py",
                ],
            }
        }
    }
    client = MCPClient(config=config)
    llm = ChatOllama(base_url="http://localhost:11434", model="qwen3.5:9b")

    trace_callbacks = None
    if _TRACE:
        from langchain_core.callbacks import StdOutCallbackHandler

        trace_callbacks = [StdOutCallbackHandler()]

    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=15,
        memory_enabled=True,
        pretty_print=True,
        verbose=_TRACE,
        callbacks=trace_callbacks,
    )

    print("\n===== Interactive MCP Chat =====")
    if _TRACE:
        print(
            "(WEATHER_AGENT_TRACE=1: debug logs on stdout/stderr; "
            "context dumps on stderr after each reply)\n",
            file=sys.stderr,
        )

    response = await agent.run("What is the weather in Tokyo?")
    print(response)  # type: ignore
    if _TRACE:
        _print_injected_context(agent, "Context after first turn (before second user message)")

    response = await agent.run("What is the forecast for Tokyo? And what is the weather in NYC?")
    print(response)  # type: ignore
    if _TRACE:
        _print_injected_context(agent, "Context after second turn")

if __name__ == "__main__":
    asyncio.run(run_memory_chat())