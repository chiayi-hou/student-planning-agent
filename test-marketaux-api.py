"""
Marketaux API
"""
import requests
from datetime import datetime, timedelta

MARKETAUX_API_KEY = "T1zKBsxfDUuHDlQ1a4zrLr4TluO4JMkuXhsiiIFY"

# get weekly news
today = datetime.now()
one_week_ago = today - timedelta(days=7)

url = "https://api.marketaux.com/v1/news/all"

# params to call request
# symbols: specify tickers of a company
# search: anything you want. | for or, + for and, - or "" can also be used
params = {
    "api_token": MARKETAUX_API_KEY,
    "search": "finance | financial markets | economy | stocks",
    "language": "en",
    "published_after": one_week_ago.strftime("%Y-%m-%d"),
    "published_before": today.strftime("%Y-%m-%d"),
    "group_similar": "true",
    "limit": 3
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()

    print("Request successful!")
    print("Number of articles:", len(data["data"]))
    print()

    for article in data["data"]:
        print("Title:", article["title"])
        print("Source:", article["source"])
        print("Published:", article["published_at"])
        print("Description:", article["description"])
        print("Snippet:", article["snippet"])
        print("URL:", article["url"])
        print("=" * 80)

else:
    print("Request failed:", response.status_code)
    print(response.text)