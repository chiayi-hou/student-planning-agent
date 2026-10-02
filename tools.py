"""The tools the harness can run, and the JSON that describes them to the model."""

import json
import requests
from datetime import datetime, timedelta, timezone

# api keys (to be removed)
ALPHA_VANTAGE_API_KEY = "HVVNJVT4CDYZW39E"

# Open-Meteo is free and needs no API key.
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

def get_financial_news(
    topic: str | None = None,
    days: int = 7
) -> str:
    """
    Get financial news from the past specified number of days.

    Args:
        topic:
            Optional financial news topic.

            Available topics include:
            - financial_markets
            - economy_monetary
            - economy_macro
            - economy_fiscal
            - finance
            - technology
            - earnings
            - mergers_and_acquisitions
            - ipo
            - energy_transportation
            - real_estate
            - life_sciences

            If the user does not specify an area, leave this as None.

        days:
            Number of days of news to retrieve.
            Default is 7 days.

    Examples:
        "What's going on recently?"
        -> topic=None, days=7

        "What happened with the Fed this week?"
        -> topic="economy_monetary", days=7

        "What happened in tech over the past month?"
        -> topic="technology", days=30
    """

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    params = {
        "function": "NEWS_SENTIMENT",
        "time_from": start_time.strftime("%Y%m%dT%H%M"),
        "time_to": now.strftime("%Y%m%dT%H%M"),
        "sort": "LATEST",
        "limit": 50,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    if topic:
        params["topics"] = topic

    try:
        response = requests.get(
            ALPHA_VANTAGE_URL,
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as e:
        return json.dumps({
            "error": f"Alpha Vantage request failed: {e}"
        })

    if "Error Message" in data:
        return json.dumps({"error": data["Error Message"]})

    if "Note" in data:
        return json.dumps({"error": data["Note"]})

    if "Information" in data:
        return json.dumps({"error": data["Information"]})

    articles = []

    for article in data.get("feed", []):
        articles.append({
            "title": article.get("title"),
            "source": article.get("source"),
            "published": article.get("time_published"),
            "summary": article.get("summary"),
            "url": article.get("url"),
        })

    return json.dumps({
        "topic": topic if topic else "all",
        "days": days,
        "article_count": len(articles),
        "articles": articles,
    })


def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    try:
        places = requests.get(GEOCODE_URL, params={"name": location, "count": 1}, timeout=10).json()
        if not places.get("results"):
            return json.dumps({"error": f"City '{location}' was not found."})
        place = places["results"][0]

        current = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
            },
            timeout=10,
        ).json()["current"]
    except requests.RequestException as e:
        # The model cannot see an exception. Return something it can reason about.
        return json.dumps({"error": f"Weather service failed: {e}"})

    return json.dumps({
        "location": place["name"],
        "temp_f": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "wind_mph": current["wind_speed_10m"],
    })


# What the model sees: the "set notes" in the screenplay.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather (temperature, humidity, wind) for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name, e.g. 'New York'"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_news",
            "description": (
                "Get a broad set of recent or past financial news for an overview, recap, "
                "or summary of what has been happening. Use this for general news requests "
                "covering a time period or financial area. Do not use this when the user "
                "mainly wants specific articles or links about a narrow topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": [
                            "finance",
                            "financial_markets",
                            "economy_monetary",
                            "economy_macro",
                            "economy_fiscal",
                            "technology",
                            "earnings",
                            "mergers_and_acquisitions",
                            "ipo",
                            "energy_transportation",
                            "real_estate",
                            "life_sciences",
                        ],
                        "description": (
                            "Optional news topic. "
                            "Use 'financial_markets' for stocks and market activity, "
                            "'economy_monetary' for the Fed, interest rates, and monetary policy, "
                            "'economy_macro' for inflation, GDP, unemployment, and macroeconomic news, "
                            "'economy_fiscal' for taxes and government spending, "
                            "'technology' for technology-related news, "
                            "'earnings' for company earnings, "
                            "and 'finance' for general finance-related news."
                        ),
                    },
                    "days": {
                        "type": "integer",
                        "description": (
                            "Number of days of news to retrieve. "
                            "Use 7 if the user does not specify a time period."
                        ),
                        "minimum": 1,
                    },
                },
                "required": [],
            },
        },
    },
]

# What the harness runs: tool name -> Python function.
TOOL_MAP = {"get_weather": get_weather, "get_financial_news": get_financial_news}


def run_tool(name: str, args: dict) -> str:
    """Run one tool call. Models invent tool names and arguments; never let that crash the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {name}: {e}"})
