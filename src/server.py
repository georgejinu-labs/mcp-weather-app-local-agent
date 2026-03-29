from fastmcp import FastMCP

from tools.weather import get_forecast, get_weather

mcp = FastMCP("Weather Server")


@mcp.tool("get_weather")
async def get_weather_tool(city: str) -> str:
    """Get the weather for a given city."""
    return await get_weather(city)


@mcp.tool("get_forecast")
async def get_forecast_tool(city: str) -> str:
    """Get the forecast for a given city."""
    return await get_forecast(city)


if __name__ == "__main__":
    mcp.run(transport="stdio")
