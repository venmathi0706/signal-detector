"""
api.py — Optional FastAPI wrapper for the signal detection system.

Exposes the pipeline as local HTTP endpoints so it can be triggered
and queried via REST — useful for integration with other tools.

Run with:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST /run                 — trigger a full detection run
    GET  /signals             — query stored signals from SQLite
    GET  /signals/{company}   — get signals for a specific competitor
    GET  /stats               — summary statistics
    GET  /health              — health check
"""

import logging
import os
import sys
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(__file__))

from signals.competitor_grievance import run as run_detector
from utils.storage import load_sqlite, get_stats_sqlite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title="Signal Detector API",
    description="Competitor Grievance Signal Detection — Vikaas.ai Assignment",
    version="1.0.0",
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "signal-detector"}


# ── Run pipeline ──────────────────────────────────────────────────────────────

@app.post("/run", tags=["Pipeline"])
def trigger_run(
    sample_only: bool = Query(False, description="Use sample data only (no network)"),
    reddit_limit: int = Query(10, description="Reddit posts per query"),
    use_rss: bool = Query(True, description="Fetch from RSS feeds"),
):
    """
    Trigger a full signal detection run.
    Results are saved to output/signals.json and output/signals.db.
    """
    try:
        signals = run_detector(
            use_reddit=not sample_only,
            use_rss=use_rss and not sample_only,
            use_sample=True,
            reddit_limit=reddit_limit,
        )
        return {
            "status": "success",
            "signals_detected": len(signals),
            "top_signals": signals[:3],  # Preview top 3
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Query signals ─────────────────────────────────────────────────────────────

@app.get("/signals", tags=["Signals"])
def get_signals(
    company: Optional[str] = Query(None, description="Filter by competitor name"),
    min_score: Optional[int] = Query(None, description="Minimum signal score"),
    signal_strength: Optional[str] = Query(None, description="high / medium / low / minimal"),
    limit: int = Query(50, description="Max results to return"),
):
    """Query stored signals from SQLite with optional filters."""
    results = load_sqlite(
        company=company,
        min_score=min_score,
        signal_strength=signal_strength,
        limit=limit,
    )
    return {"count": len(results), "signals": results}


@app.get("/signals/{company}", tags=["Signals"])
def get_signals_by_company(company: str, limit: int = Query(20)):
    """Get all signals for a specific competitor (e.g. hackerrank, hirevue)."""
    results = load_sqlite(company=company, limit=limit)
    if not results:
        raise HTTPException(status_code=404, detail=f"No signals found for: {company}")
    return {"company": company, "count": len(results), "signals": results}


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/stats", tags=["Signals"])
def get_stats():
    """Return summary statistics from the SQLite store."""
    stats = get_stats_sqlite()
    if not stats:
        return {"message": "No data yet. Run POST /run first."}
    return stats
