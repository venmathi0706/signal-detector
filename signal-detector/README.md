>> Signal Detector — Competitor Grievance Module

A modular, rule-based signal detection system that identifies negative feedback about competitor hiring/recruiting tools (HackerRank, HireVue, Codility, etc.) from 4 public data source types: forum posts, public reviews, blog comments, and search snippets.


---

>> Table of Contents
1. [Project Structure]
2. [Setup & Run Instructions]
3. [Example Input Data]
4. [Sample JSON Output]
5. [Design Explanation]
6. [Assumptions & Limitations]
7. [Constraints Met]

---

>> Project Structure

```
signal-detector/
│
├── signals/
│   ├── __init__.py
│   └── competitor_grievance.py     # Main pipeline: fetch → parse → score → save
│
├── utils/
│   ├── __init__.py
│   ├── fetcher.py                  # Forum posts: Reddit JSON API + HN RSS
│   ├── fetch_reviews.py            # Public reviews: Trustpilot, SiteJabber, Reddit
│   ├── fetch_blog_comments.py      # Blog comments: Dev.to API + HN RSS
│   ├── fetch_search_snippets.py    # Search snippets: DuckDuckGo API + HN Algolia
│   ├── parser.py                   # Competitor detection + pain point mapping
│   ├── scorer.py                   # Signal scoring logic (0–100)
│   └── storage.py                  # JSON + SQLite dual output
│
├── data/
│   └── sample_input.json           # Example input: 11 records across all 4 source types
│
├── output/
│   ├── signals.json                # Sample JSON output (generated)
│   └── signals.db                  # SQLite database (generated)
│
├── api.py                          # Optional FastAPI wrapper (local HTTP server)
├── main.py                         # CLI entry point
├── requirements.txt
└── README.md
```

---

>> Setup & Run Instructions

>> Prerequisites
- Python 3.8 or higher
- Internet connection (for live sources)

>> Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

>> Step 2 — Run the detector

Full run (all 4 sources — recommended):
```bash
python main.py
```

**Sample data only (offline, for testing):**
```bash
python main.py --sample-only
```

Other options:
```bash
python main.py --no-reddit            # Skip Reddit fetching
python main.py --no-rss               # Skip RSS feeds
python main.py --no-reviews           # Skip public reviews
python main.py --no-blog-comments     # Skip blog comments
python main.py --no-search-snippets   # Skip search snippets
python main.py --reddit-limit 5       # Limit Reddit posts per query
```

Output is saved automatically to:
- `output/signals.json` — full JSON list
- `output/signals.db` — SQLite database

>> Step 3 — Optional: Start the FastAPI server

Open a second terminal in the same folder:
```bash
uvicorn api:app --reload --port 8000
```

Then open in browser:

| URL | Description |
|---|---|
| http://localhost:8000/docs | Interactive Swagger UI |
| http://localhost:8000/signals | All detected signals |
| http://localhost:8000/signals/hackerrank | Filter by competitor |
| http://localhost:8000/signals?min_score=70 | Filter by score |
| http://localhost:8000/stats | Summary statistics |
| http://localhost:8000/health | Health check |

---

>> Example Input Data

Located at `data/sample_input.json` — 11 records covering all 4 source types:

| Source Type | Example |
|---|---|
| `forum_post` | Reddit post: "HackerRank is way too expensive for what it offers" |
| `public_review` | Trustpilot review: "1 star. HackerRank is expensive and not worth the money..." |
| `blog_comment` | Dev.to comment: "HireVue's surveillance-style recording is a privacy concern..." |
| `search_snippet` | HN Algolia: "Multiple sources report HireVue AI shows bias against non-native speakers..." |

**Competitors covered in sample data:**
HackerRank, HireVue, Codility, Workday

---

>> Sample JSON Output

```json
[
  {
    "company": "hackerrank",
    "all_competitors_mentioned": ["hackerrank"],
    "signal_type": "competitor_grievance",
    "source_url": "https://reddit.com/r/recruitinghell/...",
    "source": "reddit",
    "subreddit": "recruitinghell",
    "title": "HackerRank is way too expensive for what it offers",
    "matched_keywords": [
      "expensive", "overpriced", "pricing model", "recruiter bottleneck", "weeks to hear back"
    ],
    "pain_points": {
      "cost": ["expensive", "overpriced", "pricing model"],
      "speed": ["bottleneck", "weeks to hear back"],
      "recruiter_experience": ["recruiter bottleneck"],
      "technical_issues": ["clunky"]
    },
    "signal_score": 77,
    "signal_strength": "medium",
    "detected_at": "2026-04-18T14:31:06+00:00",
    "reason": "Negative feedback detected about hackerrank — issues: cost, speed, recruiter_experience, technical_issues"
  },
  {
    "company": "hirevue",
    "all_competitors_mentioned": ["hirevue"],
    "signal_type": "competitor_grievance",
    "source_url": "https://reddit.com/r/cscareerquestions/...",
    "source": "forum_post",
    "subreddit": "cscareerquestions",
    "title": "HireVue is dehumanizing and has serious bias problems",
    "matched_keywords": [
      "bias", "biased", "unfair", "not inclusive", "ghosted", "no feedback",
      "terrible experience", "dehumanizing", "stressful", "anxiety inducing"
    ],
    "pain_points": {
      "bias": ["bias", "biased", "favors certain", "not inclusive"],
      "recruiter_experience": ["no feedback", "ghosted"],
      "candidate_experience": ["terrible experience", "dehumanizing", "stressful"]
    },
    "signal_score": 72,
    "signal_strength": "medium",
    "detected_at": "2026-04-18T14:31:06+00:00",
    "reason": "Negative feedback detected about hirevue — issues: bias, recruiter_experience, candidate_experience"
  }
]
```

> Full sample output available in `output/signals.json`

---

>> Design Explanation

>> Data Ingestion Approach

The system uses **4 independent fetcher modules**, each targeting a different public source type. All fetchers return a uniform dict shape so the parser is completely source-agnostic.

>> Source 1 — Forum Posts (`utils/fetcher.py`)
- **Reddit** via public JSON API (`reddit.com/search.json`) — no API key required
- Queries 8 complaint-focused search terms across 5 subreddits: `r/cscareerquestions`, `r/recruitinghell`, `r/jobs`, `r/ExperiencedDevs`, `r/interviews`
- **Hacker News** via HNRSS.org RSS feeds filtered by competitor name
- 1-second delay between Reddit requests to respect rate limits

>> Source 2 — Public Reviews (`utils/fetch_reviews.py`)
- **Trustpilot** and **SiteJabber** public pages scraped with BeautifulSoup
- Reddit review-targeted queries (e.g. "HackerRank review pros cons") on review-focused subreddits
- Falls back gracefully if review sites block scraping (403 handled with warning log)

>> Source 3 — Blog Comments (`utils/fetch_blog_comments.py`)
- **Dev.to public API** (`dev.to/api/articles`) — completely free, no key needed
- Fetches articles by tag (hackerrank, hirevue, hiring, interviews, recruiting)
- Also fetches **comments** for each article via `dev.to/api/comments`
- **Hacker News RSS** feeds for additional blog-style content

>> Source 4 — Search Snippets (`utils/fetch_search_snippets.py`)
- **DuckDuckGo Instant Answer API** (`api.duckduckgo.com`) — free JSON API, no key
- **HN Algolia search API** (`hn.algolia.com/api/v1/search`) — free, no key
- 12 targeted complaint queries per source (e.g. "HackerRank expensive complaints")

>> Pipeline Flow
```
fetchers (4 sources)
    ↓
raw items (uniform dict: title, body, url, source)
    ↓
parser (competitor detection + pain point mapping + sentiment)
    ↓
scorer (0–100 score)
    ↓
filter (score >= 20, must have competitor + pain point)
    ↓
deduplicate (by source_url)
    ↓
sort (by score descending)
    ↓
storage (JSON + SQLite)
```

---

>> Signal Detection Logic

Detection runs in 3 layers — **no ML, no LLM, pure rule-based**:

>> Layer 1 — Competitor Detection (`utils/parser.py`)
9 competitors with aliases matched via case-insensitive substring search:

| Competitor | Aliases |
|---|---|
| hackerrank | "hackerrank", "hacker rank" |
| hirevue | "hirevue", "hire vue" |
| codility | "codility" |
| greenhouse | "greenhouse" |
| workday | "workday" |
| lever | "lever ats", "lever hiring" |
| taleo | "taleo" |
| icims | "icims" |
| smartrecruiters | "smartrecruiters", "smart recruiters" |

>>Layer 2 — Pain Point Mapping (`utils/parser.py`)
8 categories with curated keyword lists:

| Category | Keywords include |
|---|---|
| `cost` | expensive, overpriced, pricing model, hidden fees, costly |
| `bias` | biased, unfair, discriminatory, not inclusive, prejudice |
| `speed` | slow process, bottleneck, takes forever, weeks to hear back |
| `recruiter_experience` | recruiter bottleneck, ghosted, no feedback, unresponsive |
| `technical_issues` | buggy, crashed, broken, clunky, poor ux, freezes |
| `candidate_experience` | dehumanizing, terrible experience, waste of time, frustrating |
| `accuracy` | false positive, inaccurate, flawed assessment, irrelevant questions |
| `privacy` | recording without consent, data breach, surveillance, invasive |

>> Layer 3 — Negative Sentiment (`utils/parser.py`)
18 general negative words (hate, awful, worst, cancelled, switched away, etc.) used as a score booster — not a hard requirement for signal emission.

**Emission rule:** A record must match **at least 1 competitor AND at least 1 pain point** to become a signal.

---

>> Scoring Logic (`utils/scorer.py`)

| Component | Points per unit | Cap |
|---|---|---|
| Each competitor detected | +20 pts | max 40 |
| Each pain point category matched | +12 pts | max 48 |
| Each negative sentiment word | +3 pts | max 15 |
| Reddit upvotes (log scale bonus) | variable | max 10 |
| **Total possible** | | **100** |

**Signal strength labels:**
- `high` — score ≥ 80
- `medium` — score ≥ 50
- `low` — score ≥ 25
- `minimal` — score < 25

**Minimum threshold to emit:** score ≥ 20 (filters near-zero noise)

**Example:**
A post mentioning HackerRank (1 competitor = +20) with cost + speed + recruiter_experience pain points (3 categories = +36) and 3 sentiment words (+9) scores **65 → medium**.

---

>> Storage (`utils/storage.py`)

Dual output on every run:

| Output | Format | Purpose |
|---|---|---|
| `output/signals.json` | JSON array | Human-readable, easy to inspect |
| `output/signals.db` | SQLite | Persistent across runs, queryable via API |

SQLite deduplicates on `source_url` — re-running updates existing records rather than creating duplicates.

---
>> Assumptions & Limitations

| Assumption / Limitation | Detail |
|---|---|
| **Keyword-based only** | May miss nuanced, sarcastic, or indirect negative sentiment |
| **English only** | All keyword lists are English — non-English content ignored |
| **Reddit rate limits** | 1-second delay between requests; heavy usage may get throttled |
| **JS-rendered sites blocked** | G2, Glassdoor, Capterra require JS — cannot scrape without a browser driver |
| **Review sites may return 403** | Trustpilot/SiteJabber block automated requests; falls back gracefully |
| **Live sources vary per run** | Reddit/RSS return fresh data each run — use `--sample-only` for reproducible output |
| **Deduplication is URL-based** | Same content reposted at a different URL is not deduplicated |
| **No persistence between runs for JSON** | `signals.json` is overwritten; SQLite accumulates across runs |
| **Signal score is heuristic** | Weights are manually tuned, not learned from data |

---

>> Constraints Met

| Constraint | Implementation |
|---|---|
| Python 3.x | Python 3.8+ throughout — no other language used |
| Run locally | CLI (`python main.py`) + local FastAPI server — no cloud |
| No cloud deployment | All output stored in local `output/` folder |
| No paid APIs | Reddit JSON API, HN RSS, Dev.to API, DDG API, HN Algolia — all free |
| No LLM / AI APIs | Zero ML — pure substring matching and arithmetic scoring |
| Public/free data sources | Reddit, Hacker News, Dev.to, DuckDuckGo, sample data |
| Modular / serverless-style | Each fetcher, parser, scorer, storage function is stateless and independently callable |

---

>> Dependencies

```
requests>=2.31.0       # HTTP requests for all fetchers
feedparser>=6.0.10     # RSS feed parsing (HN RSS)
beautifulsoup4>=4.12.0 # HTML parsing for review pages
lxml>=5.0.0            # HTML parser backend for BeautifulSoup
fastapi>=0.110.0       # Optional local API server
uvicorn>=0.29.0        # ASGI server to run FastAPI
```

`sqlite3` and `json` are Python standard library — no install needed.

