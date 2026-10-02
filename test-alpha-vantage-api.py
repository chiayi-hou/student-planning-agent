"""
Alpha Vantage
Test the alpha vantage api.
"""
import requests

ALPHA_VANTAGE_API_KEY = "HVVNJVT4CDYZW39E"

url = "https://www.alphavantage.co/query"

# time_from and time_to give the range of the period
# topics: default empty. create a tool to let LLM match up available topics with user's interest
# limit: how many articles to return
# ticket: learning about a specific stock


params = {
    "function": "NEWS_SENTIMENT",
    "topics": "financial_markets",
    "time_from": "20260925T0000",
    "time_to": "20261002T2359",
    "sort": "LATEST",
    "limit": 10,
    "apikey": ALPHA_VANTAGE_API_KEY

}

# articles in "feeds", a list of dictionaries
# each dict has title, summary, author, urls...
response = requests.get(url, params=params)
data = response.json()

for article in data["feed"][:5]:
    print("Title:", article["title"])
    print("Source:", article["source"])
    print("Published:", article["time_published"])
    print("Summary:", article["summary"])
    print("URL:", article["url"])
    print()