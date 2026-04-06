"""Ranker: combine multiple signals into a single ranked list of context candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass
class RankedItem:
    """A file with its composite score and per-signal breakdown."""

    path: str
    score: float
    breakdown: dict[str, float] = field(default_factory=dict)


# Default signal weights (must sum to 1.0).
DEFAULT_WEIGHTS = {
    "semantic": 0.35,
    "graph": 0.25,
    "recency": 0.20,
    "mention": 0.20,
}


def _recency_score(days_since_last_commit: float | None) -> float:
    """Map days-since-last-commit to [0, 1].  ``None`` means no history → 0."""
    if days_since_last_commit is None:
        return 0.0
    return 1.0 / (1.0 + days_since_last_commit)


def _mention_score(path: str, task: str) -> float:
    """Return 1.0 if the file name or stem appears in the task text, else 0.0."""
    name = PurePosixPath(path).name  # e.g. "database.py"
    stem = PurePosixPath(path).stem  # e.g. "database"
    task_lower = task.lower()
    # Match the filename or stem as a whole word.
    if name.lower() in task_lower:
        return 1.0
    if re.search(rf"\b{re.escape(stem.lower())}\b", task_lower):
        return 1.0
    return 0.0


def _normalize(values: list[float]) -> list[float]:
    """Min-max normalize a list of floats to [0, 1]."""
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    span = hi - lo
    if span == 0:
        # All values equal — treat them as equal (0.0 if all zero, else 1.0).
        return [0.0 if hi == 0 else 1.0] * len(values)
    return [(v - lo) / span for v in values]


class Ranker:
    """Combine semantic, graph, recency, and mention signals into ranked results."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or dict(DEFAULT_WEIGHTS)

    def rank(
        self,
        candidates: list[str],
        task: str,
        *,
        semantic_scores: dict[str, float] | None = None,
        graph_scores: dict[str, float] | None = None,
        recency_days: dict[str, float | None] | None = None,
    ) -> list[RankedItem]:
        """Score and rank *candidates* against a *task* description.

        Parameters
        ----------
        candidates:
            File paths to rank.
        task:
            Natural-language task description (used for mention detection).
        semantic_scores:
            Pre-computed cosine similarity per file (higher is better).
        graph_scores:
            Graph centrality per file (higher is better).
        recency_days:
            Days since last commit per file (``None`` = no history).

        Returns a list of ``RankedItem`` sorted by descending score.
        """
        if not candidates:
            return []

        sem = semantic_scores or {}
        graph = graph_scores or {}
        rec = recency_days or {}

        # Raw signal vectors (one per candidate, same order).
        raw_semantic = [sem.get(c, 0.0) for c in candidates]
        raw_graph = [graph.get(c, 0.0) for c in candidates]
        raw_recency = [_recency_score(rec.get(c)) for c in candidates]
        raw_mention = [_mention_score(c, task) for c in candidates]

        # Normalize each signal independently to [0, 1].
        norm_semantic = _normalize(raw_semantic)
        norm_graph = _normalize(raw_graph)
        norm_recency = _normalize(raw_recency)
        norm_mention = _normalize(raw_mention)

        w = self.weights
        items: list[RankedItem] = []
        for i, path in enumerate(candidates):
            breakdown = {
                "semantic": norm_semantic[i],
                "graph": norm_graph[i],
                "recency": norm_recency[i],
                "mention": norm_mention[i],
            }
            score = (
                w["semantic"] * breakdown["semantic"]
                + w["graph"] * breakdown["graph"]
                + w["recency"] * breakdown["recency"]
                + w["mention"] * breakdown["mention"]
            )
            items.append(RankedItem(path=path, score=score, breakdown=breakdown))

        items.sort(key=lambda it: it.score, reverse=True)
        return items
