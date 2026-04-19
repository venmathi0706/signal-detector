"""
fetcher.py — Responsible for fetching raw data from public sources.
Supports Reddit JSON API, RSS feeds, and static sample data.
"""

import requests
import logging
import json
import time
import feedparser
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "signal-detector/1.0 (assignment project)"}


def fetch_reddit_posts(query: str, limit: int = 15, subreddits: List[str] = None) -> List[Dict[str, Any]]:
    """Fetch posts from Reddit's public JSON search API."""
    results = []

    if subreddits:
        urls = [
            f"https://www.reddit.com/r/{sub}/search.json?q={query}&restrict_sr=1&limit={limit}&sort=new"
            for sub in subreddits
        ]
    else:
        urls = [f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort=new"]

    for url in urls:
        try:
            logger.info(f"Fetching Reddit: {url}")
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                pd = post.get("data", {})
                results.append({
                    "title": pd.get("title", ""),
                    "body": pd.get("selftext", ""),
                    "url": f"https://www.reddit.com{pd.get('permalink', '')}",
                    "source": "reddit",
                    "subreddit": pd.get("subreddit", ""),
                    "score": pd.get("score", 0),
                    "created_utc": pd.get("created_utc", 0),
                })
            time.sleep(1)  # Respect Reddit rate limits
        except requests.RequestException as e:
            logger.warning(f"Reddit fetch failed for query '{query}': {e}")
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Reddit parse error for query '{query}': {e}")

    return results


def fetch_rss_feed(feed_url: str) -> List[Dict[str, Any]]:
    """Fetch entries from a public RSS feed."""
    results = []
    try:
        logger.info(f"Fetching RSS: {feed_url}")
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            results.append({
                "title": entry.get("title", ""),
                "body": entry.get("summary", ""),
                "url": entry.get("link", feed_url),
                "source": "rss",
                "subreddit": "",
                "score": 0,
                "created_utc": 0,
            })
    except Exception as e:
        logger.warning(f"RSS fetch failed for {feed_url}: {e}")
    return results


def fetch_sample_data(filepath: str) -> List[Dict[str, Any]]:
    """Load sample/static input data from a local JSON file."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} sample records from {filepath}")
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load sample data from {filepath}: {e}")
        return []
