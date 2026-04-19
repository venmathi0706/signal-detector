"""
scorer.py — Calculates a signal score (0–100) based on detection richness.

Scoring Logic:
  - Each competitor detected:          +20 pts (max 40)
  - Each pain point category matched:  +12 pts (max 48)
  - Each negative sentiment word:       +3 pts (max 15)
  - Reddit upvotes bonus (log scale):   up to +10 pts

Final score is clamped to [0, 100].
"""

import math
from typing import Dict, List


COMPETITOR_WEIGHT = 20
PAIN_POINT_WEIGHT = 12
SENTIMENT_WEIGHT = 3
UPVOTE_MAX_BONUS = 10
UPVOTE_SCALE = 500  # Score at which full bonus is earned (log-scaled)


def calculate_score(
    competitors: List[str],
    pain_points: Dict[str, List[str]],
    sentiment_words: List[str],
    upvotes: int = 0,
) -> int:
    """
    Compute a 0–100 signal score.

    Args:
        competitors:     List of competitor names detected.
        pain_points:     Dict of {category: [matched phrases]}.
        sentiment_words: List of negative sentiment words found.
        upvotes:         Reddit post score (optional).

    Returns:
        Integer score between 0 and 100.
    """
    score = 0

    # Competitor presence (capped at 2 competitors for scoring)
    score += min(len(competitors), 2) * COMPETITOR_WEIGHT

    # Pain point breadth (capped at 4 categories)
    score += min(len(pain_points), 4) * PAIN_POINT_WEIGHT

    # Negative sentiment density (capped at 5 words)
    score += min(len(sentiment_words), 5) * SENTIMENT_WEIGHT

    # Reddit engagement bonus (logarithmic)
    if upvotes > 0:
        bonus = UPVOTE_MAX_BONUS * (math.log1p(upvotes) / math.log1p(UPVOTE_SCALE))
        score += min(int(bonus), UPVOTE_MAX_BONUS)

    return min(score, 100)


def score_label(score: int) -> str:
    """Return a human-readable label for the score range."""
    if score >= 80:
        return "high"
    elif score >= 50:
        return "medium"
    elif score >= 25:
        return "low"
    else:
        return "minimal"
