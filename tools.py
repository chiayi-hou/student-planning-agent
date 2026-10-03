"""The tools the harness can run, and the JSON that describes them to the model."""

import json
import requests
from datetime import datetime, timedelta, timezone

# api keys (to be removed)
ALPHA_VANTAGE_API_KEY = "HVVNJVT4CDYZW39E"
MARKETAUX_API_KEY = "T1zKBsxfDUuHDlQ1a4zrLr4TluO4JMkuXhsiiIFY"

# define url used
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
MARKETAUX_URL = "https://api.marketaux.com/v1/news/all"


def get_financial_news(
    topic: str | None = None,
    days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Get financial news for a specified time period.

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
            Number of days of news to retrieve when no specific start date
            is provided. Default is 7 days.

        start_date:
            Optional start date in YYYY-MM-DD format.

        end_date:
            Optional end date in YYYY-MM-DD format.
            If omitted, the current date is used.

    Examples:
        "What's going on recently?"
        -> topic=None, days=7

        "What happened with the Fed this week?"
        -> topic="economy_monetary", days=7

        "What happened in tech over the past month?"
        -> topic="technology", days=30

        "What happened in finance last December?"
        -> topic="finance",
           start_date="2025-12-01",
           end_date="2025-12-31"

        "What happened in markets from March 1 to March 15, 2026?"
        -> topic="financial_markets",
           start_date="2026-03-01",
           end_date="2026-03-15"
    """

    now = datetime.now(timezone.utc)

    try:
        if end_date:
            end_time = datetime.strptime(
                end_date, "%Y-%m-%d"
            ).replace(
                hour=23,
                minute=59,
                tzinfo=timezone.utc
            )
        else:
            end_time = now

        if start_date:
            start_time = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        else:
            start_time = end_time - timedelta(days=days)

    except ValueError:
        return json.dumps({
            "error": "Dates must use YYYY-MM-DD format."
        })

    if start_time > end_time:
        return json.dumps({
            "error": "start_date must be before end_date."
        })

    params = {
        "function": "NEWS_SENTIMENT",
        "time_from": start_time.strftime("%Y%m%dT%H%M"),
        "time_to": end_time.strftime("%Y%m%dT%H%M"),
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
        "start_date": start_time.strftime("%Y-%m-%d"),
        "end_date": end_time.strftime("%Y-%m-%d"),
        "article_count": len(articles),
        "articles": articles,
    })

def search_financial_news(
    query: str,
    start_date: str | None = None,
    end_date: str | None = None,
    symbol: str | None = None,
) -> str:

    now = datetime.now(timezone.utc)

    if end_date is None:
        end_date = now.strftime("%Y-%m-%d")

    if start_date is None:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    params = {
        "api_token": MARKETAUX_API_KEY,
        "search": query,
        "language": "en",
        "group_similar": "true",
        "limit": 3,
        "published_after": start_date,
        "published_before": end_date,
    }

    if symbol:
        params["symbols"] = symbol

    try:
        response = requests.get(
            MARKETAUX_URL,
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as e:
        return json.dumps({
            "error": f"Marketaux request failed: {e}"
        })

    articles = []

    for article in data.get("data", []):
        articles.append({
            "title": article.get("title"),
            "source": article.get("source"),
            "published": article.get("published_at"),
            "description": article.get("description"),
            "snippet": article.get("snippet"),
            "url": article.get("url"),
            "uuid": article.get("uuid"),
        })

    return json.dumps({
        "query": query,
        "symbol": symbol,
        "article_count": len(articles),
        "articles": articles,
    })

# What the model sees: the "set notes" in the screenplay.
TOOLS = [
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
                        "Number of days of news to retrieve when the user does not specify "
                        "an exact start date. Use 7 if the user does not specify a time period. "
                        "For example, use 30 for 'the past 30 days'."
                    ),
                    "minimum": 1,
                },
                "start_date": {
                    "type": "string",
                    "description": (
                        "Optional start date in YYYY-MM-DD format. Use this when the user "
                        "specifies a historical period or exact date range, such as "
                        "'last December' or 'from March 1 to March 15'."
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "Optional end date in YYYY-MM-DD format. Use this with start_date "
                        "when the user specifies a historical period or exact date range. "
                        "If the user gives a start date but no end date, leave this unspecified."
                    ),
                },
            },
            "required": [],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "search_financial_news",
        "description": (
            "Search for financial news about a specific topic, company, or event. "
            "Use this when the user asks about a narrow subject, such as a particular "
            "company, event, technology, policy issue, or market development. "
            "This tool returns only a small number of highly relevant articles, so do not "
            "use it for broad financial news summaries, general news catch-ups, or requests "
            "asking what has been happening overall. "
            "Use get_financial_news instead for broad overviews, recaps, or summaries."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The specific topic, company, or event to search for, such as "
                        "'AI data center electricity demand', 'Nvidia Blackwell chips', "
                        "or 'Federal Reserve rate cuts'."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": (
                        "Optional start date in YYYY-MM-DD format. "
                        "If the user specifies a historical or exact time period, provide it. "
                        "If omitted, the tool searches the most recent 30 days."
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "Optional end date in YYYY-MM-DD format. "
                        "If omitted, the current date is used."
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": (
                        "Optional stock ticker when the request is about a specific company, "
                        "such as NVDA, AAPL, or TSLA."
                    ),
                },
            },
            "required": ["query"],
        },
    },
},
]

# What the harness runs: tool name -> Python function.
TOOL_MAP = {"get_financial_news": get_financial_news, "search_financial_news": search_financial_news}


def run_tool(name: str, args: dict) -> str:
    """Run one tool call. Models invent tool names and arguments; never let that crash the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {name}: {e}"})
