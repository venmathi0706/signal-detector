"""
fetch_reviews.py — Fetches public reviews about competitor tools.

Uses Trustpilot + SiteJabber public pages + Reddit review-targeted queries.
G2/Capterra block scraping with 403; these alternatives are publicly accessible.
"""

import requests
import logging
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; signal-detector/1.0)"}

TRUSTPILOT_URLS = [
    "https://www.trustpilot.com/review/www.hackerrank.com",
    "https://www.trustpilot.com/review/www.hirevue.com",
]

PUBLIC_REVIEW_PAGES = {
    "hackerrank": "https://www.sitejabber.com/reviews/hackerrank.com",
    "hirevue":    "https://www.sitejabber.com/reviews/hirevue.com",
}

REVIEW_REDDIT_QUERIES = [
    "HackerRank review pros cons",
    "HireVue review honest opinion",
    "Codility review experience",
    "is HackerRank worth it",
    "HireVue honest review candidate",
    "Codility assessment review",
]

REVIEW_SUBREDDITS = ["cscareerquestions", "recruitinghell", "ExperiencedDevs", "jobs"]


def _scrape_page(url: str, company: str, platform: str) -> List[Dict[str, Any]]:
    """Generic page scraper — extracts paragraph text blocks."""
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"{platform} returned {resp.status_code} for {url}")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        blocks = soup.select("p") 
        for block in blocks[:10]:
            text = block.get_text(strip=True)
            if len(text) > 50:
                results.append({
                    "title": f"{platform} review: {company}",
                    "body": text[:800],
                    "url": url,
                    "source": "public_review",
                    "subreddit": "",
                    "score": 0,
                    "created_utc": 0,
                    "platform": platform,
                })
        time.sleep(2)
    except Exception as e:
        logger.warning(f"{platform} fetch failed ({url}): {e}")
    return results


def fetch_reddit_reviews() -> List[Dict[str, Any]]:
    """Fetch review-style Reddit posts — most reliable free review source."""
    from utils.fetcher import fetch_reddit_posts
    results = []
    for query in REVIEW_REDDIT_QUERIES:
        items = fetch_reddit_posts(query, limit=8, subreddits=REVIEW_SUBREDDITS)
        for item in items:
            item["source"] = "public_review"
            item["platform"] = "reddit_review"
        results.extend(items)
        time.sleep(1)
    return results


def fetch_all_reviews(max_per_tool: int = 5) -> List[Dict[str, Any]]:
    """Fetch public reviews from Trustpilot, SiteJabber, and Reddit."""
    results = []

    for url in TRUSTPILOT_URLS:
        company = url.split("www.")[-1].replace(".com", "")
        results.extend(_scrape_page(url, company, "trustpilot"))

    for company, url in PUBLIC_REVIEW_PAGES.items():
        results.extend(_scrape_page(url, company, "sitejabber"))

    results.extend(fetch_reddit_reviews())

    logger.info(f"Total public review items fetched: {len(results)}")
    return results
