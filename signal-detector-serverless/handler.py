"""
handler.py — Serverless Framework function handlers.

Each function maps to a `serverless.yml` entry and wraps the existing
pipeline logic with a Lambda-compatible (event, context) → response interface.

Run locally:
    serverless invoke local -f run
    serverless invoke local -f runSampleOnly
    serverless invoke local -f getSignals
    serverless invoke local -f health

Or via HTTP with serverless-offline:
    serverless offline
    curl -X POST http://localhost:8000/run
    curl http://localhost:8000/signals
    curl http://localhost:8000/stats
    curl http://localhost:8000/health
"""

import json
import logging
import os
import sys

# Ensure the project root is on the path (needed for serverless invoke local)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(body: dict, status: int = 200) -> dict:
    """Return a Lambda proxy-compatible success response."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def _error(message: str, status: int = 500) -> dict:
    """Return a Lambda proxy-compatible error response."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }


def _query_param(event: dict, key: str, default=None):
    """Safely extract a query string parameter from the event."""
    qs = event.get("queryStringParameters") or {}
    return qs.get(key, default)


def _path_param(event: dict, key: str, default=None):
    """Safely extract a path parameter from the event."""
    pp = event.get("pathParameters") or {}
    return pp.get(key, default)


# ── Function: run ─────────────────────────────────────────────────────────────

def run(event: dict, context):
    """
    POST /run — Trigger a full signal detection pipeline run.

    Query parameters (all optional):
      sample_only=true     Use local sample data only (no network)
      reddit_limit=10      Reddit posts per query
      use_rss=true         Include Hacker News RSS
    """
    try:
        sample_only  = _query_param(event, "sample_only", "false").lower() == "true"
        reddit_limit = int(_query_param(event, "reddit_limit", "10"))
        use_rss      = _query_param(event, "use_rss", "true").lower() == "true"

        logger.info(
            f"[run] sample_only={sample_only}, reddit_limit={reddit_limit}, use_rss={use_rss}"
        )

        from signals.competitor_grievance import run as run_detector

        signals = run_detector(
            use_reddit        = not sample_only,
            use_rss           = use_rss and not sample_only,
            use_reviews       = not sample_only,
            use_blog_comments = not sample_only,
            use_search_snippets = not sample_only,
            use_sample        = True,
            reddit_limit      = reddit_limit,
        )

        return _ok({
            "status":           "success",
            "signals_detected": len(signals),
            "top_signals":      signals[:3],
        })

    except Exception as exc:
        logger.exception("run handler failed")
        return _error(str(exc))


# ── Function: runSampleOnly ───────────────────────────────────────────────────

def run_sample_only(event: dict, context):
    """
    Direct invoke only (no HTTP event) — runs sample data with no network calls.
    Use: serverless invoke local -f runSampleOnly
    """
    try:
        logger.info("[runSampleOnly] Running with local sample data only")

        from signals.competitor_grievance import run as run_detector

        signals = run_detector(
            use_reddit          = False,
            use_rss             = False,
            use_reviews         = False,
            use_blog_comments   = False,
            use_search_snippets = False,
            use_sample          = True,
        )

        # Print a readable summary when invoked from CLI
        print(f"\n{'='*60}")
        print(f"  SAMPLE RUN COMPLETE — {len(signals)} signals detected")
        print(f"{'='*60}")
        for s in signals:
            print(
                f"  [{s['signal_score']:>3}] {s['signal_strength']:<8} "
                f"{s['company']:<16} — {', '.join(list(s['pain_points'].keys())[:3])}"
            )
        print(f"{'='*60}\n")

        return _ok({
            "status":           "success",
            "signals_detected": len(signals),
            "signals":          signals,
        })

    except Exception as exc:
        logger.exception("runSampleOnly handler failed")
        return _error(str(exc))


# ── Function: getSignals ──────────────────────────────────────────────────────

def get_signals(event: dict, context):
    """
    GET /signals — Query stored signals with optional filters.

    Query parameters:
      company          Filter by competitor name (partial match)
      min_score        Minimum signal score (integer)
      signal_strength  high / medium / low / minimal
      limit            Max results (default 50)
    """
    try:
        company         = _query_param(event, "company")
        signal_strength = _query_param(event, "signal_strength")
        limit           = int(_query_param(event, "limit", "50"))

        raw_min_score   = _query_param(event, "min_score")
        min_score       = int(raw_min_score) if raw_min_score is not None else None

        from utils.storage import load_sqlite

        results = load_sqlite(
            company         = company,
            min_score       = min_score,
            signal_strength = signal_strength,
            limit           = limit,
        )

        return _ok({"count": len(results), "signals": results})

    except Exception as exc:
        logger.exception("get_signals handler failed")
        return _error(str(exc))


# ── Function: getSignalsByCompany ─────────────────────────────────────────────

def get_signals_by_company(event: dict, context):
    """
    GET /signals/{company} — Signals for a specific competitor.
    """
    try:
        company = _path_param(event, "company")
        limit   = int(_query_param(event, "limit", "20"))

        if not company:
            return _error("Missing path parameter: company", status=400)

        from utils.storage import load_sqlite

        results = load_sqlite(company=company, limit=limit)

        if not results:
            return _error(f"No signals found for: {company}", status=404)

        return _ok({"company": company, "count": len(results), "signals": results})

    except Exception as exc:
        logger.exception("get_signals_by_company handler failed")
        return _error(str(exc))


# ── Function: getStats ────────────────────────────────────────────────────────

def get_stats(event: dict, context):
    """
    GET /stats — Summary statistics from SQLite.
    """
    try:
        from utils.storage import get_stats_sqlite

        stats = get_stats_sqlite()

        if not stats:
            return _ok({"message": "No data yet. Run POST /run first."})

        return _ok(stats)

    except Exception as exc:
        logger.exception("get_stats handler failed")
        return _error(str(exc))


# ── Function: health ──────────────────────────────────────────────────────────

def health(event: dict, context):
    """GET /health — Health check."""
    return _ok({"status": "ok", "service": "signal-detector"})
