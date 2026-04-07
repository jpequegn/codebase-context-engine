"""Tests for git history enrichment."""

import subprocess
import textwrap
from pathlib import Path

from ctx.git_history import CommitSummary, GitHistory


def _init_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with a few commits."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, capture_output=True
    )

    # Commit 1: add app.py
    (repo / "app.py").write_text("print('hello')")
    subprocess.run(["git", "add", "app.py"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add app.py"], cwd=repo, capture_output=True
    )

    # Commit 2: add db.py
    (repo / "db.py").write_text("conn = None")
    subprocess.run(["git", "add", "db.py"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add db.py"], cwd=repo, capture_output=True
    )

    # Commit 3: modify app.py
    (repo / "app.py").write_text("print('hello world')")
    subprocess.run(["git", "add", "app.py"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Update app greeting"], cwd=repo, capture_output=True
    )

    return repo


def test_for_file(tmp_path):
    repo = _init_repo(tmp_path)
    history = GitHistory(str(repo))

    commits = history.for_file("app.py", last_n=5)
    assert len(commits) == 2
    assert commits[0].message == "Update app greeting"
    assert commits[1].message == "Add app.py"
    assert all(isinstance(c, CommitSummary) for c in commits)


def test_for_file_last_n(tmp_path):
    repo = _init_repo(tmp_path)
    history = GitHistory(str(repo))

    commits = history.for_file("app.py", last_n=1)
    assert len(commits) == 1
    assert commits[0].message == "Update app greeting"


def test_for_files(tmp_path):
    repo = _init_repo(tmp_path)
    history = GitHistory(str(repo))

    result = history.for_files(["app.py", "db.py"], last_n=3)
    assert "app.py" in result
    assert "db.py" in result
    assert len(result["app.py"]) == 2
    assert len(result["db.py"]) == 1


def test_recent_files(tmp_path):
    repo = _init_repo(tmp_path)
    history = GitHistory(str(repo))

    recent = history.recent_files(days=1)
    # All commits are from today, so both files should appear
    assert "app.py" in recent
    assert "db.py" in recent
    # app.py was modified most recently, should be first
    assert recent.index("app.py") < recent.index("db.py")


def test_commit_summary_fields(tmp_path):
    repo = _init_repo(tmp_path)
    history = GitHistory(str(repo))

    commits = history.for_file("app.py", last_n=1)
    c = commits[0]
    assert len(c.hash) == 8
    assert c.author == "Test User"
    assert c.date is not None
    assert c.insertions >= 0
    assert c.deletions >= 0
    assert "app.py" in c.files_changed


def test_for_file_nonexistent(tmp_path):
    repo = _init_repo(tmp_path)
    history = GitHistory(str(repo))

    commits = history.for_file("nonexistent.py")
    assert commits == []
