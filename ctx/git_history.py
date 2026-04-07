"""Git history enrichment: recent commits per file."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import git


@dataclass
class CommitSummary:
    hash: str
    message: str
    author: str
    date: datetime
    files_changed: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


class GitHistory:
    """Query git history for temporal context about files."""

    def __init__(self, repo_path: str):
        self._repo = git.Repo(repo_path)

    def for_file(self, path: str, last_n: int = 5) -> list[CommitSummary]:
        """Get the last N commits that touched a specific file."""
        commits = list(self._repo.iter_commits(paths=path, max_count=last_n))
        return [self._summarize(c) for c in commits]

    def for_files(
        self, paths: list[str], last_n: int = 3
    ) -> dict[str, list[CommitSummary]]:
        """Get recent commits for multiple files."""
        return {path: self.for_file(path, last_n) for path in paths}

    def recent_files(self, days: int = 7) -> list[str]:
        """Files touched in the last N days, sorted by most recent first."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        seen_order: list[str] = []
        seen: set[str] = set()

        for commit in self._repo.iter_commits():
            commit_date = commit.committed_datetime
            if commit_date < since:
                break
            for path in commit.stats.files:
                if path not in seen:
                    seen.add(path)
                    seen_order.append(path)

        return seen_order

    def _summarize(self, commit: git.Commit) -> CommitSummary:
        stats = commit.stats.total
        return CommitSummary(
            hash=commit.hexsha[:8],
            message=commit.message.strip().split("\n")[0],
            author=str(commit.author),
            date=commit.committed_datetime,
            files_changed=list(commit.stats.files.keys()),
            insertions=stats.get("insertions", 0),
            deletions=stats.get("deletions", 0),
        )
