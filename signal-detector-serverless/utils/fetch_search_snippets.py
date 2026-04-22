"""
fetch_search_snippets.py — Fetches search snippets using SerpAPI-free alternatives.

Uses:
  - DuckDuckGo Instant Answer API (free, JSON, no key needed)
  - HackerNews Algolia search API (free, no key needed)
  - Reddit search as search snippets
"""

import requests
import logging
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "signal-detector/1.0"}

SEARCH_QUERIES = [
    "HackerRank expensive complaints",
    "HireVue bias unfair",
    "Codility slow frustrating",
    "HackerRank recruiter bottleneck",
    "HireVue privacy recording",
    "Codility broken bugs",
    "HackerRank bad candidate experience",
    "HireVue worst interview",
    "Workday ATS bottleneck",
    "Greenhouse ATS expensive",
    "hiring assessment platform complaints",
    "technical interview bias slow",
]

# HN Algolia search — completely free, no key
HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"


def fetch_duckduckgo_answer(query: str) -> List[Dict[str, Any]]:
    """
    DuckDuckGo Instant Answer API — completely free JSON API, no key needed.
    Returns abstract/answer snippets for queries.
    """
    results = []
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
    try:
        logger.info(f"DuckDuckGo Instant Answer: '{query}'")
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Extract abstract
            abstract = data.get("Abstract", "")
            if abstract and len(abstract) > 30:
                results.append({
                    "title": data.get("Heading", query),
                    "body": abstract,
                    "url": data.get("AbstractURL", url),
                    "source": "search_snippet",
                    "subreddit": "",
                    "score": 0,
                    "created_utc": 0,
                    "platform": "duckduckgo",
                    "query": query,
                })
            # Extract related topics
            for topic in data.get("RelatedTopics", [])[:3]:
                text = topic.get("Text", "")
                if text and len(text) > 30:
                    results.append({
                        "title": f"Related: {query}",
                        "body": text,
                        "url": topic.get("FirstURL", url),
                        "source": "search_snippet",
                        "subreddit": "",
                        "score": 0,
                        "created_utc": 0,
                        "platform": "duckduckgo",
                        "query": query,
                    })
        time.sleep(1)
    except Exception as e:
        logger.warning(f"DuckDuckGo API failed for '{query}': {e}")
    return results


def fetch_hn_search_snippets(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    HN Algolia search API — completely free, returns HN posts/comments as snippets.
    """
    results = []
    try:
        logger.info(f"HN Algolia search: '{query}'")
        params = {"query": query, "hitsPerPage": max_results, "tags": "comment,story"}
        resp = requests.get(HN_ALGOLIA, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for hit in hits:
                text = hit.get("comment_text") or hit.get("story_text") or hit.get("title", "")
                if text and len(text) > 30:
                    results.append({
                        "title": hit.get("title") or f"HN: {query}",
                        "body": text[:800],
                        "url": f"https://news.ycombinator.com/item?id={hit.get('objectID','')}",
                        "source": "search_snippet",
                        "subreddit": "",
                        "score": hit.get("points", 0) or 0,
                        "created_utc": 0,
                        "platform": "hackernews_search",
                        "query": query,
                    })
        time.sleep(1)
    except Exception as e:
        logger.warning(f"HN Algolia search failed for '{query}': {e}")
    return results


def fetch_all_search_snippets(max_per_query: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch search snippets from DuckDuckGo Instant Answer API + HN Algolia.
    Both are completely free with no API key required.
    """
    results = []

    for query in SEARCH_QUERIES:
        # DuckDuckGo Instant Answer (JSON API)
        results.extend(fetch_duckduckgo_answer(query))
        # HN Algolia full-text search
        results.extend(fetch_hn_search_snippets(query, max_results=max_per_query))

    logger.info(f"Total search snippet items fetched: {len(results)}")
    return results
