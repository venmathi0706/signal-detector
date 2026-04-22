# Signal Detector — Competitor Grievance Module

Detects negative feedback about competitor hiring tools (HackerRank, HireVue, Codility, etc.)
from public sources: Reddit, RSS feeds, Dev.to, Hacker News, DuckDuckGo, and review sites.

Built for the Vikaas.ai platform assignment.

---

## Architecture

```
signal-detector/
├── serverless.yml          ← Serverless Framework config (functions + local HTTP)
├── handler.py              ← Serverless function handlers (wraps pipeline)
├── main.py                 ← CLI entry point (alternative to serverless)
├── api.py                  ← FastAPI wrapper (alternative to serverless)
├── signals/
│   └── competitor_grievance.py   ← Core orchestration: fetch → parse → score → store
├── utils/
│   ├── fetcher.py                ← Reddit JSON API + RSS + sample data
│   ├── fetch_reviews.py          ← Trustpilot, SiteJabber, Reddit reviews
│   ├── fetch_blog_comments.py    ← Dev.to API + HN RSS
│   ├── fetch_search_snippets.py  ← DuckDuckGo + HN Algolia
│   ├── parser.py                 ← Competitor + pain point + sentiment detection
│   ├── scorer.py                 ← 0–100 signal scoring
│   └── storage.py                ← JSON + SQLite persistence
├── data/
│   └── sample_input.json         ← Local sample data (no network required)
└── output/
    ├── signals.json              ← Generated output (JSON)
    └── signals.db                ← Generated output (SQLite)
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Serverless Framework)

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Serverless Framework

```bash
npm install -g serverless
```

### 3. Install the serverless-offline plugin (local HTTP server)

```bash
npm install --save-dev serverless-offline
```

---

## Running with Serverless Framework (Primary Method)

### Option A — Direct function invoke (no HTTP server needed)

Run sample data only (fastest, no network):
```bash
serverless invoke local -f runSampleOnly
```

Run full pipeline (Reddit + RSS + reviews + blog comments + search snippets):
```bash
serverless invoke local -f run
```

Run with parameters:
```bash
serverless invoke local -f run --data '{"queryStringParameters": {"sample_only": "true"}}'
serverless invoke local -f run --data '{"queryStringParameters": {"reddit_limit": "5"}}'
```

Query stored signals:
```bash
serverless invoke local -f getSignals
serverless invoke local -f getSignals --data '{"queryStringParameters": {"min_score": "50"}}'
serverless invoke local -f getSignals --data '{"queryStringParameters": {"company": "hackerrank"}}'
```

Get stats:
```bash
serverless invoke local -f getStats
```

### Option B — Local HTTP server (serverless-offline)

```bash
serverless offline
```

Then call via HTTP:
```bash
# Trigger a full run
curl -X POST "http://localhost:8000/run"

# Run with sample data only (no network)
curl -X POST "http://localhost:8000/run?sample_only=true"

# Query signals
curl "http://localhost:8000/signals"
curl "http://localhost:8000/signals?company=hackerrank&min_score=50"
curl "http://localhost:8000/signals/hirevue"

# Stats
curl "http://localhost:8000/stats"

# Health check
curl "http://localhost:8000/health"
```

---

## Alternative: CLI Runner (no Serverless)

```bash
python main.py                        # Full run — all sources
python main.py --sample-only          # Sample data only (no network)
python main.py --no-reddit            # Skip Reddit
python main.py --no-reviews           # Skip reviews
python main.py --reddit-limit 5       # Limit Reddit posts per query
```

## Alternative: FastAPI (no Serverless)

```bash
uvicorn api:app --reload --port 8000
```

Docs available at: http://localhost:8000/docs

---

## Output Format

Signals are saved to `output/signals.json` and `output/signals.db`.

Example signal record:
```json
{
  "company": "hackerrank",
  "all_competitors_mentioned": ["hackerrank"],
  "signal_type": "competitor_grievance",
  "source_url": "https://reddit.com/r/recruitinghell/...",
  "source": "reddit",
  "subreddit": "recruitinghell",
  "title": "HackerRank is way too expensive for what it offers",
  "matched_keywords": ["expensive", "recruiter bottleneck", "overpriced"],
  "pain_points": {
    "cost": ["expensive", "overpriced"],
    "speed": ["recruiter bottleneck"]
  },
  "signal_score": 76,
  "signal_strength": "medium",
  "detected_at": "2024-04-22T10:30:00+00:00",
  "reason": "Negative feedback detected about hackerrank — issues: cost, speed"
}
```

---

## Scoring Logic

| Component                | Points       | Cap     |
|--------------------------|--------------|---------|
| Competitor detected      | +20 each     | max 40  |
| Pain point category      | +12 each     | max 48  |
| Negative sentiment word  | +3 each      | max 15  |
| Reddit upvote bonus      | log-scale    | max 10  |
| **Total**                |              | **100** |

Strength labels: `high` >=80 · `medium` >=50 · `low` >=25 · `minimal` <25

---

## Signal Detection Logic

**Competitors tracked:** HackerRank, HireVue, Codility, Greenhouse, Lever, Workday, Taleo, iCIMS, SmartRecruiters, Pymetrics

**Pain point categories:** cost · bias · speed · recruiter_experience · technical_issues · candidate_experience · accuracy · privacy

**Data sources:**
- Reddit JSON API (no key needed) — r/cscareerquestions, r/recruitinghell, etc.
- Hacker News RSS via hnrss.org
- Dev.to public API (no key needed)
- HN Algolia search API (free, no key)
- DuckDuckGo Instant Answer API (free, no key)
- Trustpilot + SiteJabber public pages
- Local sample data (data/sample_input.json)

---

## Assumptions & Limitations

- Reddit may rate-limit requests; the fetcher sleeps 1s between requests
- Trustpilot/SiteJabber may return 403; the scraper degrades gracefully
- DuckDuckGo Instant Answer API returns limited results for niche queries
- No paid APIs or LLMs are used anywhere in the pipeline
- Signal deduplication is URL-based; near-duplicate posts are not merged
- Minimum signal score threshold is 20 (configurable in competitor_grievance.py)
