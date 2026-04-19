"""
storage.py — Handles persisting signal records to both JSON and SQLite.

Supports:
  - save_json()   : Write signals list to a JSON file
  - save_sqlite() : Upsert signals into a local SQLite database
  - load_sqlite() : Query signals back from SQLite with optional filters
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "signals.json")
DEFAULT_DB_PATH   = os.path.join(os.path.dirname(__file__), "..", "output", "signals.db")

# ── JSON ──────────────────────────────────────────────────────────────────────

def save_json(signals: List[Dict[str, Any]], path: str = DEFAULT_JSON_PATH) -> None:
    """Write signal list to a JSON file, creating directories as needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2, ensure_ascii=False)
    logger.info(f"JSON output saved → {path}  ({len(signals)} records)")


def load_json(path: str = DEFAULT_JSON_PATH) -> List[Dict[str, Any]]:
    """Load signals from a JSON file."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ── SQLite ────────────────────────────────────────────────────────────────────

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS signals (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company                 TEXT NOT NULL,
    all_competitors         TEXT,           -- JSON array
    signal_type             TEXT NOT NULL,
    source_url              TEXT UNIQUE,    -- dedup key
    source                  TEXT,
    subreddit               TEXT,
    title                   TEXT,
    matched_keywords        TEXT,           -- JSON array
    pain_points             TEXT,           -- JSON object
    signal_score            INTEGER,
    signal_strength         TEXT,
    detected_at             TEXT,
    reason                  TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);
"""

_UPSERT = """
INSERT INTO signals (
    company, all_competitors, signal_type, source_url, source,
    subreddit, title, matched_keywords, pain_points,
    signal_score, signal_strength, detected_at, reason
) VALUES (
    :company, :all_competitors, :signal_type, :source_url, :source,
    :subreddit, :title, :matched_keywords, :pain_points,
    :signal_score, :signal_strength, :detected_at, :reason
)
ON CONFLICT(source_url) DO UPDATE SET
    signal_score     = excluded.signal_score,
    signal_strength  = excluded.signal_strength,
    pain_points      = excluded.pain_points,
    matched_keywords = excluded.matched_keywords,
    detected_at      = excluded.detected_at;
"""


def _get_conn(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def _serialize(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten JSON fields for SQLite storage."""
    return {
        "company":          signal.get("company", ""),
        "all_competitors":  json.dumps(signal.get("all_competitors_mentioned", [])),
        "signal_type":      signal.get("signal_type", ""),
        "source_url":       signal.get("source_url", ""),
        "source":           signal.get("source", ""),
        "subreddit":        signal.get("subreddit", ""),
        "title":            signal.get("title", ""),
        "matched_keywords": json.dumps(signal.get("matched_keywords", [])),
        "pain_points":      json.dumps(signal.get("pain_points", {})),
        "signal_score":     signal.get("signal_score", 0),
        "signal_strength":  signal.get("signal_strength", ""),
        "detected_at":      signal.get("detected_at", datetime.now(timezone.utc).isoformat()),
        "reason":           signal.get("reason", ""),
    }


def _deserialize(row: sqlite3.Row) -> Dict[str, Any]:
    """Expand SQLite row back to signal dict."""
    d = dict(row)
    d["all_competitors_mentioned"] = json.loads(d.pop("all_competitors", "[]"))
    d["matched_keywords"]          = json.loads(d.get("matched_keywords", "[]"))
    d["pain_points"]               = json.loads(d.get("pain_points", "{}"))
    return d


def save_sqlite(signals: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> None:
    """Upsert signals into SQLite (deduplicates on source_url)."""
    conn = _get_conn(db_path)
    rows = [_serialize(s) for s in signals]
    with conn:
        conn.executemany(_UPSERT, rows)
    conn.close()
    logger.info(f"SQLite output saved → {db_path}  ({len(signals)} records upserted)")


def load_sqlite(
    db_path: str = DEFAULT_DB_PATH,
    company: Optional[str] = None,
    min_score: Optional[int] = None,
    signal_strength: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Query signals from SQLite with optional filters.

    Args:
        company:         Filter by competitor name (partial match)
        min_score:       Minimum signal_score
        signal_strength: 'high', 'medium', 'low', 'minimal'
        limit:           Max records to return
    """
    if not os.path.exists(db_path):
        return []

    conn = _get_conn(db_path)
    query = "SELECT * FROM signals WHERE 1=1"
    params: List[Any] = []

    if company:
        query += " AND company LIKE ?"
        params.append(f"%{company}%")
    if min_score is not None:
        query += " AND signal_score >= ?"
        params.append(min_score)
    if signal_strength:
        query += " AND signal_strength = ?"
        params.append(signal_strength)

    query += " ORDER BY signal_score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_deserialize(r) for r in rows]


def get_stats_sqlite(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Return summary statistics from the SQLite store."""
    if not os.path.exists(db_path):
        return {}
    conn = _get_conn(db_path)
    total      = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    by_company = conn.execute(
        "SELECT company, COUNT(*) as cnt FROM signals GROUP BY company ORDER BY cnt DESC"
    ).fetchall()
    avg_score  = conn.execute("SELECT AVG(signal_score) FROM signals").fetchone()[0]
    conn.close()
    return {
        "total_signals": total,
        "average_score": round(avg_score or 0, 1),
        "by_company": [{"company": r[0], "count": r[1]} for r in by_company],
    }
