"""
parser.py — Parses raw text to detect competitor mentions and negative sentiment phrases.
Maps detected phrases to categorized pain points.
"""

import re
from typing import List, Dict, Tuple

# ── Competitor definitions ────────────────────────────────────────────────────
COMPETITORS = {
    "hackerrank": ["hackerrank", "hacker rank"],
    "hirevue": ["hirevue", "hire vue"],
    "codility": ["codility"],
    "greenhouse": ["greenhouse"],
    "lever": ["lever ats", "lever hiring"],
    "workday": ["workday"],
    "taleo": ["taleo"],
    "icims": ["icims"],
    "smartrecruiters": ["smartrecruiters", "smart recruiters"],
    "pymetrics": ["pymetrics"],
}

# ── Pain point categories with associated keywords ────────────────────────────
PAIN_POINTS = {
    "cost": [
        "expensive", "overpriced", "costly", "too much money", "price hike",
        "pricing model", "not worth", "overcharge", "high cost", "budget issue",
        "subscription cost", "hidden fees",
    ],
    "bias": [
        "bias", "biased", "unfair", "discriminatory", "discrimination",
        "not diverse", "lack of diversity", "prejudice", "skewed results",
        "favors certain", "not inclusive",
    ],
    "speed": [
        "slow process", "slow", "takes forever", "bottleneck", "delayed",
        "too long", "weeks to hear back", "months to hear", "laggy", "sluggish",
        "not responsive", "time consuming",
    ],
    "recruiter_experience": [
        "recruiter bottleneck", "no feedback", "ghosted", "ghosting",
        "no response", "unresponsive recruiter", "bad recruiter", "poor communication",
        "lack of communication", "left hanging",
    ],
    "technical_issues": [
        "bug", "buggy", "crashed", "broken", "doesn't work", "error",
        "glitch", "technical issue", "keeps crashing", "unusable", "freezes",
        "poor ux", "bad interface", "clunky",
    ],
    "candidate_experience": [
        "terrible experience", "horrible", "awful", "worst platform",
        "dehumanizing", "impersonal", "stressful", "anxiety inducing",
        "not candidate friendly", "poor experience", "waste of time",
        "frustrating", "annoying",
    ],
    "accuracy": [
        "false positive", "false negative", "wrong results", "inaccurate",
        "not accurate", "flawed assessment", "poor assessment", "doesn't measure",
        "irrelevant questions", "outdated questions",
    ],
    "privacy": [
        "privacy concern", "data breach", "tracking", "surveillance",
        "recording without consent", "spyware", "invasive", "intrusive",
        "privacy violation", "data collection",
    ],
}

# ── General negative sentiment words (lightweight sentiment layer) ─────────────
NEGATIVE_SENTIMENT_WORDS = [
    "hate", "terrible", "horrible", "awful", "worst", "bad", "poor",
    "disappointing", "frustrating", "annoying", "broken", "useless",
    "waste", "scam", "avoid", "not recommend", "switched away",
    "cancelled", "churned", "looking for alternative",
]


def clean_text(text: str) -> str:
    """Lowercase and normalize whitespace."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_competitors(text: str) -> List[str]:
    """Return list of competitor canonical names found in text."""
    text_clean = clean_text(text)
    found = []
    for canonical, aliases in COMPETITORS.items():
        for alias in aliases:
            if alias in text_clean:
                if canonical not in found:
                    found.append(canonical)
                break
    return found


def detect_pain_points(text: str) -> Dict[str, List[str]]:
    """Return dict of {pain_point_category: [matched_phrases]}."""
    text_clean = clean_text(text)
    matched = {}
    for category, phrases in PAIN_POINTS.items():
        hits = [phrase for phrase in phrases if phrase in text_clean]
        if hits:
            matched[category] = hits
    return matched


def detect_negative_sentiment(text: str) -> List[str]:
    """Return list of general negative sentiment words found."""
    text_clean = clean_text(text)
    return [word for word in NEGATIVE_SENTIMENT_WORDS if word in text_clean]


def extract_matched_keywords(pain_points: Dict[str, List[str]]) -> List[str]:
    """Flatten pain point matches into a single keyword list."""
    keywords = []
    for hits in pain_points.values():
        keywords.extend(hits)
    return list(set(keywords))


def analyze(text: str) -> Tuple[List[str], Dict[str, List[str]], List[str]]:
    """
    Full analysis of a text block.
    Returns: (competitors, pain_points, negative_sentiment_words)
    """
    competitors = detect_competitors(text)
    pain_points = detect_pain_points(text)
    sentiment = detect_negative_sentiment(text)
    return competitors, pain_points, sentiment
