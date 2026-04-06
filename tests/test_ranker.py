"""Tests for the multi-signal ranker."""

from ctx.ranker import Ranker, _mention_score, _normalize


# ---------------------------------------------------------------------------
# Acceptance criterion: mentioned file always ranks #1
# ---------------------------------------------------------------------------

def test_mentioned_file_ranks_first():
    """Task 'fix the duplicate key error in database.py' → database.py is #1."""
    candidates = ["models.py", "database.py", "utils.py"]
    task = "fix the duplicate key error in database.py"

    ranker = Ranker()
    results = ranker.rank(candidates, task)

    assert results[0].path == "database.py"
    assert results[0].breakdown["mention"] == 1.0


def test_mentioned_stem_ranks_first():
    """Mentioning 'database' (no extension) still matches database.py."""
    candidates = ["models.py", "database.py", "utils.py"]
    task = "fix the duplicate key error in database"

    ranker = Ranker()
    results = ranker.rank(candidates, task)

    assert results[0].path == "database.py"


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------

def test_mention_score_exact_filename():
    assert _mention_score("src/database.py", "look at database.py") == 1.0


def test_mention_score_stem():
    assert _mention_score("src/database.py", "check the database module") == 1.0


def test_mention_score_no_match():
    assert _mention_score("src/database.py", "update the models") == 0.0


def test_mention_score_case_insensitive():
    assert _mention_score("src/Database.py", "fix database") == 1.0


def test_normalize_different_values():
    assert _normalize([0.0, 5.0, 10.0]) == [0.0, 0.5, 1.0]


def test_normalize_all_zeros():
    assert _normalize([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]


def test_normalize_all_same_nonzero():
    assert _normalize([3.0, 3.0]) == [1.0, 1.0]


def test_normalize_empty():
    assert _normalize([]) == []


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def test_all_signals_combined():
    """When all signals are provided, the composite score uses all weights."""
    candidates = ["a.py", "b.py"]
    task = "refactor a.py"

    ranker = Ranker()
    results = ranker.rank(
        candidates,
        task,
        semantic_scores={"a.py": 0.9, "b.py": 0.1},
        graph_scores={"a.py": 0.8, "b.py": 0.2},
        recency_days={"a.py": 0, "b.py": 30},
    )

    assert results[0].path == "a.py"
    # All four signals should appear in the breakdown.
    assert set(results[0].breakdown.keys()) == {"semantic", "graph", "recency", "mention"}


def test_scores_between_zero_and_one():
    """Composite scores must be in [0, 1]."""
    candidates = ["x.py", "y.py", "z.py"]
    task = "optimize x.py"

    ranker = Ranker()
    results = ranker.rank(
        candidates,
        task,
        semantic_scores={"x.py": 1.0, "y.py": 0.5, "z.py": 0.0},
        graph_scores={"x.py": 1.0, "y.py": 0.5, "z.py": 0.0},
        recency_days={"x.py": 0, "y.py": 10, "z.py": 100},
    )

    for item in results:
        assert 0.0 <= item.score <= 1.0


def test_empty_candidates():
    ranker = Ranker()
    assert ranker.rank([], "some task") == []


def test_no_optional_signals():
    """Ranker works with only the task string (mention signal only)."""
    candidates = ["foo.py", "bar.py"]
    task = "update foo.py"

    ranker = Ranker()
    results = ranker.rank(candidates, task)

    assert results[0].path == "foo.py"
    assert results[0].breakdown["mention"] == 1.0


def test_custom_weights():
    """Custom weights override the defaults."""
    candidates = ["a.py", "b.py"]
    task = "unrelated task"

    # Only care about semantic similarity.
    ranker = Ranker(weights={"semantic": 1.0, "graph": 0.0, "recency": 0.0, "mention": 0.0})
    results = ranker.rank(
        candidates,
        task,
        semantic_scores={"a.py": 0.2, "b.py": 0.9},
    )

    assert results[0].path == "b.py"


def test_results_sorted_descending():
    candidates = ["a.py", "b.py", "c.py"]
    task = "work on c.py"

    ranker = Ranker()
    results = ranker.rank(
        candidates,
        task,
        semantic_scores={"a.py": 0.1, "b.py": 0.5, "c.py": 0.3},
    )

    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
