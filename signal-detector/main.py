"""
main.py — CLI entry point for the Signal Detection system.

Usage:
    python main.py                        # Full run — all sources
    python main.py --sample-only          # Sample data only (no network)
    python main.py --no-reddit            # Skip Reddit
    python main.py --no-reviews           # Skip G2/Capterra reviews
    python main.py --no-blog-comments     # Skip Dev.to/Hackernoon
    python main.py --no-search-snippets   # Skip Bing/DuckDuckGo snippets
    python main.py --reddit-limit 5       # Limit Reddit posts per query
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Signal Detector — Competitor Grievance Module"
    )
    parser.add_argument("--sample-only", action="store_true",
        help="Only use local sample data (no network)")
    parser.add_argument("--no-reddit", action="store_true",
        help="Skip Reddit fetching")
    parser.add_argument("--no-rss", action="store_true",
        help="Skip RSS feed fetching")
    parser.add_argument("--no-reviews", action="store_true",
        help="Skip G2/Capterra public reviews")
    parser.add_argument("--no-blog-comments", action="store_true",
        help="Skip Dev.to/Hackernoon blog comments")
    parser.add_argument("--no-search-snippets", action="store_true",
        help="Skip Bing/DuckDuckGo search snippets")
    parser.add_argument("--reddit-limit", type=int, default=10,
        help="Reddit posts per query (default: 10)")
    return parser.parse_args()


def print_summary(signals):
    print("\n" + "=" * 65)
    print(f"  SIGNAL DETECTION COMPLETE — {len(signals)} signals found")
    print("=" * 65)

    if not signals:
        print("  No signals detected above minimum threshold.")
        return

    # Group by source type
    sources = {}
    for s in signals:
        src = s.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("\n  Sources breakdown:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        label = {
            "reddit": "Forum Posts (Reddit)",
            "rss": "Forum Posts (HN RSS)",
            "public_review": "Public Reviews (G2/Capterra)",
            "blog_comment": "Blog Comments (Dev.to/Hackernoon)",
            "search_snippet": "Search Snippets (Bing/DuckDuckGo)",
            "sample": "Sample Data",
        }.get(src, src)
        print(f"    {label:<40} {count} signals")

    print(f"\n  {'SCORE':<8} {'STRENGTH':<10} {'COMPANY':<18} {'SOURCE':<18} {'PAIN POINTS'}")
    print("  " + "-" * 70)
    for s in signals[:20]:
        pain = ", ".join(list(s["pain_points"].keys())[:3])
        src = s.get("source", "")[:16]
        print(
            f"  {s['signal_score']:<8} {s['signal_strength']:<10} "
            f"{s['company']:<18} {src:<18} {pain}"
        )

    print(f"\n  Output saved to: output/signals.json + output/signals.db")
    print("=" * 65 + "\n")


def main():
    args = parse_args()
    logger.info("Starting Competitor Grievance Signal Detector")
    logger.info("Sources: Forum Posts | Public Reviews | Blog Comments | Search Snippets")

    from signals.competitor_grievance import run

    signals = run(
        use_reddit=not args.no_reddit and not args.sample_only,
        use_rss=not args.no_rss and not args.sample_only,
        use_reviews=not args.no_reviews and not args.sample_only,
        use_blog_comments=not args.no_blog_comments and not args.sample_only,
        use_search_snippets=not args.no_search_snippets and not args.sample_only,
        use_sample=True,
        reddit_limit=args.reddit_limit,
    )

    print_summary(signals)


if __name__ == "__main__":
    main()
