import asyncio

from langchain_ollama import ChatOllama
from mcp_use import MCPAgent, MCPClient

async def run_memory_chat():
    config = {
        "mcpServers": {
            "weather": {
                "command": "uv",
                "args": [
                    "run",
                    "src/server.py"
                ]
            }
        }
    }
    # Create MCPClient from config file
    client = MCPClient(config=config)
    llm = ChatOllama(base_url="http://localhost:11434", model="qwen3.5:9b")

    # Create agent with memory_enabled=True
    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=15,
        memory_enabled=True,  # Enable built-in conversation memory
        pretty_print=True,
    )

    print("\n===== Interactive MCP Chat =====")
    response = await agent.run("What is the weather in Tokyo?")
    print(response) # type: ignore

    response = await agent.run("What is the forecast for Tokyo? And what is the weather in NYC?")
    print(response) # type: ignore

if __name__ == "__main__":
    asyncio.run(run_memory_chat())