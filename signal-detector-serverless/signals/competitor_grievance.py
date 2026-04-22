"""
competitor_grievance.py — Signal module for detecting negative feedback
about competitor hiring/recruiting tools from public data sources.

This module orchestrates: fetch → parse → score → output.
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

from utils.fetcher import fetch_reddit_posts, fetch_rss_feed, fetch_sample_data
from utils.fetch_reviews import fetch_all_reviews
from utils.fetch_blog_comments import fetch_all_blog_comments
from utils.fetch_search_snippets import fetch_all_search_snippets
from utils.parser import analyze, extract_matched_keywords
from utils.scorer import calculate_score, score_label
from utils.storage import save_json, save_sqlite

logger = logging.getLogger(__name__)

# ── Source configuration ──────────────────────────────────────────────────────

REDDIT_QUERIES = [
    "HackerRank bad experience",
    "HireVue problems complaints",
    "Codility frustrating",
    "HackerRank expensive bias",
    "HireVue slow unfair",
    "Codility recruiter bottleneck",
    "hiring assessment tool complaints",
    "ATS software bad review",
]

REDDIT_SUBREDDITS = [
    "cscareerquestions",
    "recruitinghell",
    "jobs",
    "ExperiencedDevs",
    "interviews",
]

RSS_FEEDS = [
    "https://hnrss.org/newest?q=HackerRank",
    "https://hnrss.org/newest?q=HireVue",
    "https://hnrss.org/newest?q=Codility",
]

SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_input.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "signals.json")

# ── Minimum thresholds ────────────────────────────────────────────────────────
MIN_SCORE = 20  # Discard very weak signals


def build_signal_record(
    item: Dict[str, Any],
    competitors: List[str],
    pain_points: Dict[str, List[str]],
    sentiment_words: List[str],
) -> Dict[str, Any]:
    """Construct a structured signal record."""
    score = calculate_score(
        competitors,
        pain_points,
        sentiment_words,
        upvotes=item.get("score", 0),
    )
    matched_keywords = extract_matched_keywords(pain_points)
    matched_keywords += sentiment_words

    return {
        "company": competitors[0] if competitors else "unknown",
        "all_competitors_mentioned": competitors,
        "signal_type": "competitor_grievance",
        "source_url": item.get("url", ""),
        "source": item.get("source", "unknown"),
        "subreddit": item.get("subreddit", ""),
        "title": item.get("title", ""),
        "matched_keywords": list(set(matched_keywords)),
        "pain_points": pain_points,
        "signal_score": score,
        "signal_strength": score_label(score),
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "reason": _build_reason(competitors, pain_points),
    }


def _build_reason(competitors: List[str], pain_points: Dict[str, List[str]]) -> str:
    """Generate a human-readable reason string."""
    comp_str = ", ".join(competitors) if competitors else "unknown tool"
    pain_str = ", ".join(pain_points.keys()) if pain_points else "general dissatisfaction"
    return f"Negative feedback detected about {comp_str} — issues: {pain_str}"


def deduplicate(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate signals based on source URL."""
    seen_urls = set()
    unique = []
    for signal in signals:
        url = signal.get("source_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(signal)
    return unique


def process_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run parse + score on a list of raw fetched items."""
    signals = []
    for item in items:
        full_text = f"{item.get('title', '')} {item.get('body', '')}"
        if not full_text.strip():
            continue

        competitors, pain_points, sentiment_words = analyze(full_text)

        # Must mention at least one competitor AND have at least one pain point
        if not competitors or not pain_points:
            continue

        record = build_signal_record(item, competitors, pain_points, sentiment_words)

        if record["signal_score"] >= MIN_SCORE:
            signals.append(record)
            logger.info(
                f"  ✓ Signal detected [{record['signal_score']}] — "
                f"{record['company']} via {record['source']}"
            )

    return signals


def run(
    use_reddit: bool = True,
    use_rss: bool = True,
    use_sample: bool = True,
    use_reviews: bool = True,
    use_blog_comments: bool = True,
    use_search_snippets: bool = True,
    reddit_limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Main entry point for the competitor grievance signal detector.

    Sources:
        - Reddit (forum posts)
        - Hacker News RSS (forum posts)
        - G2 + Capterra (public reviews)
        - Dev.to + Hackernoon (blog comments)
        - Bing + DuckDuckGo (search snippets)
        - Local sample data

    Returns:
        List of signal records written to output/signals.json + signals.db
    """
    all_items: List[Dict[str, Any]] = []

    # 1. Forum posts: Reddit
    if use_reddit:
        logger.info("=== [Forum Posts] Fetching from Reddit ===")
        for query in REDDIT_QUERIES:
            items = fetch_reddit_posts(
                query, limit=reddit_limit, subreddits=REDDIT_SUBREDDITS
            )
            all_items.extend(items)

    # 2. Forum posts: RSS (Hacker News)
    if use_rss:
        logger.info("=== [Forum Posts] Fetching from Hacker News RSS ===")
        for feed_url in RSS_FEEDS:
            items = fetch_rss_feed(feed_url)
            all_items.extend(items)

    # 3. Public reviews: G2 + Capterra
    if use_reviews:
        logger.info("=== [Public Reviews] Fetching from G2 + Capterra ===")
        items = fetch_all_reviews(max_per_tool=5)
        all_items.extend(items)

    # 4. Blog comments: Dev.to + Hackernoon
    if use_blog_comments:
        logger.info("=== [Blog Comments] Fetching from Dev.to + Hackernoon ===")
        items = fetch_all_blog_comments()
        all_items.extend(items)

    # 5. Search snippets: Bing + DuckDuckGo
    if use_search_snippets:
        logger.info("=== [Search Snippets] Fetching from Bing + DuckDuckGo ===")
        items = fetch_all_search_snippets(max_per_query=5)
        all_items.extend(items)

    # 6. Sample / static data
    if use_sample:
        logger.info("=== [Sample Data] Loading local sample data ===")
        items = fetch_sample_data(SAMPLE_DATA_PATH)
        all_items.extend(items)

    logger.info(f"Total raw items collected: {len(all_items)}")

    # ── 4. Process ─────────────────────────────────────────────────────────
    logger.info("=== Processing items ===")
    signals = process_items(all_items)

    # ── 5. Deduplicate & sort ──────────────────────────────────────────────
    signals = deduplicate(signals)
    signals.sort(key=lambda x: x["signal_score"], reverse=True)

    # ── 6. Save output — JSON + SQLite ─────────────────────────────────────
    save_json(signals, OUTPUT_PATH)
    save_sqlite(signals)

    logger.info(f"=== Done: {len(signals)} signals saved to JSON + SQLite ===")
    return signals
