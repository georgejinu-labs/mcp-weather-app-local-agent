import pytest

from tools.weather import format_current_weather, format_forecast


def _sample_current_payload() -> dict:
    return {
        "current_condition": [
            {
                "temp_C": "12",
                "weatherDesc": [{"value": "Sunny"}],
                "humidity": "65",
                "windspeedKmph": "10",
                "winddir16Point": "NE",
                "gustKmph": "15",
            }
        ],
    }


def _sample_forecast_payload() -> dict:
    return {
        "forecast": [
            {
                "hourly": [
                    {
                        "tempC": "14",
                        "weatherDesc": [{"value": "Partly cloudy"}],
                        "humidity": "70",
                        "windspeedKmph": "8",
                        "winddir16Point": "SW",
                        "gustKmph": "12",
                    }
                ]
            }
        ],
    }


def test_format_current_weather() -> None:
    text = format_current_weather(_sample_current_payload(), "London")
    assert "London" in text
    assert "Sunny" in text
    assert "12°C" in text
    assert "65%" in text
    assert "10 km/h" in text
    assert "NE" in text
    assert "gust speed of 15 km/h" in text


def test_format_current_weather_omits_gust_when_absent() -> None:
    payload = {
        "current_condition": [
            {
                "temp_C": "3",
                "weatherDesc": [{"value": "Partly cloudy"}],
                "humidity": "23",
                "windspeedKmph": "23",
                "winddir16Point": "NW",
            }
        ],
    }
    text = format_current_weather(payload, "NYC")
    assert "Partly cloudy" in text
    assert "gust speed" not in text


def test_format_forecast() -> None:
    text = format_forecast(_sample_forecast_payload(), "Paris")
    assert "Paris" in text
    assert "Partly cloudy" in text
    assert "14°C" in text


def test_format_forecast_uses_weather_key_and_wind_gust_kmph() -> None:
    payload = {
        "weather": [
            {
                "hourly": [
                    {
                        "tempC": "4",
                        "weatherDesc": [{"value": "Clear"}],
                        "humidity": "58",
                        "windspeedKmph": "19",
                        "winddir16Point": "NNW",
                        "WindGustKmph": "24",
                    }
                ]
            }
        ],
    }
    text = format_forecast(payload, "London")
    assert "gust speed of 24 km/h" in text


@pytest.mark.parametrize("bad_key", ["current_condition", "forecast"])
def test_format_functions_need_structure(bad_key: str) -> None:
    payload: dict = {bad_key: []}
    with pytest.raises(IndexError):
        if bad_key == "current_condition":
            format_current_weather(payload, "X")
        else:
            format_forecast(payload, "X")
