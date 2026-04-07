"""ContextEngine: main assembly orchestrator."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ctx.budget import BudgetPacker, ContextItem
from ctx.embeddings import EmbedFn, SemanticSearch
from ctx.git_history import GitHistory
from ctx.graph import CallGraph
from ctx.parsers.python import parse_directory
from ctx.ranker import RankedItem, Ranker


def _detect_mentioned_files(task: str, all_files: list[str]) -> set[str]:
    """Find files explicitly mentioned in the task description."""
    mentioned = set()
    task_lower = task.lower()
    for f in all_files:
        name = Path(f).name.lower()
        stem = Path(f).stem.lower()
        if name in task_lower or re.search(rf"\b{re.escape(stem)}\b", task_lower):
            mentioned.add(f)
    return mentioned


class ContextEngine:
    """Orchestrates the full context assembly pipeline."""

    def __init__(
        self,
        repo_path: str,
        budget_tokens: int = 8000,
        embed_fn: EmbedFn | None = None,
    ):
        self.repo_path = repo_path
        self.budget_tokens = budget_tokens
        self._embed_fn = embed_fn

        # Lazy-initialized components
        self._graph: CallGraph | None = None
        self._ranker = Ranker()
        self._packer = BudgetPacker(budget_tokens)
        self._search: SemanticSearch | None = None
        self._all_files: list[str] | None = None

    def _ensure_graph(self) -> CallGraph:
        if self._graph is None:
            self._graph = CallGraph()
            self._graph.build(self.repo_path)
            self._all_files = self._graph.files
        return self._graph

    def _ensure_search(self) -> SemanticSearch:
        if self._search is None:
            cache_path = str(Path(self.repo_path) / ".ctx_cache.db")
            self._search = SemanticSearch(
                cache_path=cache_path, embed_fn=self._embed_fn
            )
            self._search.index(self.repo_path)
        return self._search

    def assemble(
        self, task: str, *, use_semantic: bool = True
    ) -> tuple[list[ContextItem], list[RankedItem]]:
        """Assemble context for a task. Returns (packed items, full ranking)."""
        graph = self._ensure_graph()
        all_files = self._all_files or []

        # 1. Detect mentioned files
        mentioned = _detect_mentioned_files(task, all_files)

        # 2. Graph expansion
        depth_map: dict[str, int] = {}
        graph_candidates: set[str] = set()
        for f in mentioned:
            for dep in graph.dependencies(f, depth=1):
                depth_map.setdefault(dep, 1)
                graph_candidates.add(dep)
            for dep in graph.dependencies(f, depth=2):
                depth_map.setdefault(dep, 2)
                graph_candidates.add(dep)

        # 3. Semantic search
        semantic_scores: dict[str, float] = {}
        if use_semantic:
            try:
                search = self._ensure_search()
                results = search.query(task, top_k=20)
                for r in results:
                    # Keep best similarity per file
                    if r.path not in semantic_scores or r.similarity > semantic_scores[r.path]:
                        semantic_scores[r.path] = r.similarity
            except Exception:
                pass  # Semantic search is optional (API key may not be set)

        # 4. Git enrichment
        recency_days: dict[str, float | None] = {}
        try:
            git_hist = GitHistory(self.repo_path)
            now = datetime.now(timezone.utc)
            for f in all_files:
                commits = git_hist.for_file(f, last_n=1)
                if commits:
                    delta = now - commits[0].date
                    recency_days[f] = delta.total_seconds() / 86400
                else:
                    recency_days[f] = None
        except Exception:
            pass  # Not a git repo, skip

        # 5. Combine candidates
        candidates = list(
            set(all_files) | mentioned | graph_candidates | set(semantic_scores.keys())
        )

        # 6. Rank
        graph_centrality = graph.centrality()
        ranked = self._ranker.rank(
            candidates,
            task,
            semantic_scores=semantic_scores,
            graph_scores=graph_centrality,
            recency_days=recency_days,
        )

        # 7. Pack into budget
        ranked_paths = [(item.path, item.score) for item in ranked]
        items = self._packer.pack(
            ranked_paths,
            self.repo_path,
            mentioned_files=mentioned,
            depth_map=depth_map,
        )

        return items, ranked

    def assemble_prompt(self, items: list[ContextItem]) -> str:
        """Format items as a markdown prompt."""
        return self._packer.assemble_prompt(items)

    def total_tokens(self, items: list[ContextItem]) -> int:
        """Total token count."""
        return self._packer.total_tokens(items)

    def close(self) -> None:
        if self._search is not None:
            self._search.close()
