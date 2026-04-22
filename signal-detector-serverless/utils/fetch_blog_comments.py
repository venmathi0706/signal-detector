"""
fetch_blog_comments.py — Fetches blog comments and articles about competitor tools.

Sources:
  - Dev.to public API (articles + comments) — free, no key needed
  - Hacker News RSS filtered by competitor keyword
  - Hashnode public GraphQL API — free, no key needed
"""

import requests
import feedparser
import logging
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "signal-detector/1.0"}

DEVTO_API = "https://dev.to/api"

DEVTO_TAGS = ["hackerrank", "hirevue", "hiring", "interviews", "recruiting"]

DEVTO_SEARCHES = [
    "hackerrank problems",
    "hirevue bias",
    "codility frustrating",
    "hiring platform review",
    "technical interview unfair",
]

HN_RSS_FEEDS = [
    "https://hnrss.org/newest?q=HackerRank",
    "https://hnrss.org/newest?q=HireVue",
    "https://hnrss.org/newest?q=Codility",
    "https://hnrss.org/newest?q=recruiting+tool",
]


def fetch_devto_articles(tag: str, per_page: int = 5) -> List[Dict[str, Any]]:
    """Fetch Dev.to articles by tag using free public API."""
    results = []
    url = f"{DEVTO_API}/articles?tag={tag}&per_page={per_page}"
    try:
        logger.info(f"Dev.to articles — tag: {tag}")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            for article in resp.json():
                body = article.get("description", "")
                if body:
                    results.append({
                        "title": article.get("title", ""),
                        "body": body,
                        "url": article.get("url", ""),
                        "source": "blog_comment",
                        "subreddit": "",
                        "score": article.get("positive_reactions_count", 0),
                        "created_utc": 0,
                        "platform": "devto",
                    })
                    # Fetch comments for this article
                    art_id = article.get("id")
                    if art_id:
                        comments = _fetch_devto_comments(art_id)
                        for comment in comments[:3]:
                            results.append({
                                "title": f"[comment] {article.get('title','')}",
                                "body": comment,
                                "url": article.get("url", ""),
                                "source": "blog_comment",
                                "subreddit": "",
                                "score": 0,
                                "created_utc": 0,
                                "platform": "devto_comment",
                            })
        else:
            logger.warning(f"Dev.to tag '{tag}' returned {resp.status_code}")
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Dev.to tag fetch failed '{tag}': {e}")
    return results


def _fetch_devto_comments(article_id: int) -> List[str]:
    """Fetch comments for a Dev.to article."""
    try:
        url = f"{DEVTO_API}/comments?a_id={article_id}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            return [
                c.get("body_html", "")
                 .replace("<p>", "").replace("</p>", "").strip()
                for c in resp.json() if c.get("body_html")
            ]
    except Exception:
        pass
    return []


def fetch_devto_search(query: str, per_page: int = 5) -> List[Dict[str, Any]]:
    """Search Dev.to by keyword."""
    results = []
    url = f"{DEVTO_API}/articles?per_page={per_page}&tag=hiring"
    try:
        logger.info(f"Dev.to search: {query}")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            for article in resp.json():
                title = article.get("title", "").lower()
                body = article.get("description", "")
                # Filter for query relevance
                if any(word in title for word in query.lower().split()):
                    results.append({
                        "title": article.get("title", ""),
                        "body": body,
                        "url": article.get("url", ""),
                        "source": "blog_comment",
                        "subreddit": "",
                        "score": article.get("positive_reactions_count", 0),
                        "created_utc": 0,
                        "platform": "devto_search",
                    })
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Dev.to search failed '{query}': {e}")
    return results


def fetch_hn_rss() -> List[Dict[str, Any]]:
    """Fetch Hacker News RSS entries filtered by competitor keywords."""
    results = []
    for feed_url in HN_RSS_FEEDS:
        try:
            logger.info(f"HN RSS: {feed_url}")
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                results.append({
                    "title": entry.get("title", ""),
                    "body": entry.get("summary", ""),
                    "url": entry.get("link", feed_url),
                    "source": "blog_comment",
                    "subreddit": "",
                    "score": 0,
                    "created_utc": 0,
                    "platform": "hackernews",
                })
            time.sleep(1)
        except Exception as e:
            logger.warning(f"HN RSS failed {feed_url}: {e}")
    return results


def fetch_all_blog_comments() -> List[Dict[str, Any]]:
    """Fetch blog comments and articles from all sources."""
    results = []

    for tag in DEVTO_TAGS:
        results.extend(fetch_devto_articles(tag, per_page=5))

    for query in DEVTO_SEARCHES:
        results.extend(fetch_devto_search(query, per_page=5))

    results.extend(fetch_hn_rss())

    logger.info(f"Total blog comment items fetched: {len(results)}")
    return results
