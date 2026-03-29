from __future__ import annotations

import httpx

WTTR_J1_URL = "https://wttr.in/~{city}?format=j1"


def _gust_kmph(block: dict) -> str | None:
    """wttr.in uses `gustKmph` in some blocks and `WindGustKmph` in hourly data; both may be absent."""
    raw = block.get("gustKmph") or block.get("WindGustKmph")
    if raw is None or raw == "":
        return None
    return str(raw)


def format_current_weather(weather: dict, city: str) -> str:
    """Build the user-facing string from wttr.in `format=j1` JSON (current condition)."""
    current = weather["current_condition"][0]
    desc = current["weatherDesc"][0]["value"]
    temp = current["temp_C"]
    humidity = current["humidity"]
    wind_speed = current["windspeedKmph"]
    wind_direction = current["winddir16Point"]
    gust = _gust_kmph(current)
    gust_clause = f" and gust speed of {gust} km/h" if gust else ""
    return (
        f"The weather in {city} is {desc} with a temperature of {temp}°C, "
        f"humidity of {humidity}%, wind speed of {wind_speed} km/h from the {wind_direction} "
        f"direction{gust_clause}."
    )


def _first_forecast_hour(weather: dict) -> dict:
    """wttr.in j1 uses `forecast` in some builds and `weather` (daily list) in others."""
    if "forecast" in weather:
        return weather["forecast"][0]["hourly"][0]
    return weather["weather"][0]["hourly"][0]


def format_forecast(weather: dict, city: str) -> str:
    """Build the user-facing string from wttr.in `format=j1` JSON (first forecast hour)."""
    hourly = _first_forecast_hour(weather)
    desc = hourly["weatherDesc"][0]["value"]
    temp = hourly["tempC"]
    humidity = hourly["humidity"]
    wind_speed = hourly["windspeedKmph"]
    wind_direction = hourly["winddir16Point"]
    gust = _gust_kmph(hourly)
    gust_clause = f" and gust speed of {gust} km/h" if gust else ""
    return (
        f"The forecast for {city} is {desc} with a temperature of {temp}°C, "
        f"humidity of {humidity}%, wind speed of {wind_speed} km/h from the {wind_direction} "
        f"direction{gust_clause}."
    )


async def get_weather(city: str, *, client: httpx.AsyncClient | None = None) -> str:
    url = WTTR_J1_URL.format(city=city)

    async def _fetch(c: httpx.AsyncClient) -> str:
        response = await c.get(url)
        if response.status_code != 200:
            return f"Error: {response.status_code}"
        return format_current_weather(response.json(), city)

    if client is not None:
        return await _fetch(client)
    async with httpx.AsyncClient() as c:
        return await _fetch(c)


async def get_forecast(city: str, *, client: httpx.AsyncClient | None = None) -> str:
    url = WTTR_J1_URL.format(city=city)

    async def _fetch(c: httpx.AsyncClient) -> str:
        response = await c.get(url)
        if response.status_code != 200:
            return f"Error: {response.status_code}"
        return format_forecast(response.json(), city)

    if client is not None:
        return await _fetch(client)
    async with httpx.AsyncClient() as c:
        return await _fetch(c)
