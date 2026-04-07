"""Semantic search: embed files by function, cache by mtime."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


@dataclass
class Chunk:
    path: str
    name: str  # function/class name, or "__module__" for module-level
    content: str
    start_line: int
    end_line: int


@dataclass
class SearchResult:
    path: str
    chunk_name: str
    content: str
    similarity: float
    start_line: int


def function_chunks(path: str, source: str) -> list[Chunk]:
    """Split a Python file into per-function/class chunks using AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [Chunk(path=path, name="__module__", content=source, start_line=1, end_line=len(source.splitlines()))]

    lines = source.splitlines()
    chunks: list[Chunk] = []
    covered: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1  # 0-indexed
            end = node.end_lineno or node.lineno
            chunk_lines = lines[start:end]
            if chunk_lines:
                chunks.append(
                    Chunk(
                        path=path,
                        name=node.name,
                        content="\n".join(chunk_lines),
                        start_line=node.lineno,
                        end_line=end,
                    )
                )
                covered.update(range(start, end))

    # Collect uncovered module-level code
    module_lines = [
        lines[i] for i in range(len(lines)) if i not in covered and lines[i].strip()
    ]
    if module_lines:
        chunks.insert(
            0,
            Chunk(
                path=path,
                name="__module__",
                content="\n".join(module_lines),
                start_line=1,
                end_line=len(lines),
            ),
        )

    return chunks


class EmbeddingCache:
    """SQLite-backed cache for embeddings, keyed by content hash."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS embeddings (
                content_hash TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                chunk_name TEXT NOT NULL,
                embedding BLOB NOT NULL,
                mtime REAL NOT NULL
            )"""
        )
        self._conn.commit()

    def get(self, content_hash: str) -> list[float] | None:
        row = self._conn.execute(
            "SELECT embedding FROM embeddings WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def put(
        self,
        content_hash: str,
        path: str,
        chunk_name: str,
        embedding: list[float],
        mtime: float,
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO embeddings
               (content_hash, path, chunk_name, embedding, mtime)
               VALUES (?, ?, ?, ?, ?)""",
            (content_hash, path, chunk_name, json.dumps(embedding), mtime),
        )
        self._conn.commit()

    def invalidate_path(self, path: str, current_mtime: float) -> None:
        """Remove stale entries for a path whose mtime has changed."""
        self._conn.execute(
            "DELETE FROM embeddings WHERE path = ? AND mtime != ?",
            (path, current_mtime),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


# Type for embedding functions: takes list of strings, returns list of vectors
EmbedFn = Callable[[list[str]], list[list[float]]]


def openai_embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed texts using OpenAI's text-embedding-3-small model."""
    import openai

    client = openai.OpenAI()
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]


class SemanticSearch:
    """Semantic search over a codebase using embeddings."""

    def __init__(
        self,
        cache_path: str = ".ctx_cache.db",
        embed_fn: EmbedFn | None = None,
    ):
        self._cache = EmbeddingCache(cache_path)
        self._embed_fn = embed_fn or openai_embed_batch
        self._chunks: list[Chunk] = []
        self._embeddings: list[np.ndarray] = []

    def index(self, directory: str) -> int:
        """Index all Python files in a directory. Returns number of chunks indexed."""
        root = Path(directory)
        self._chunks = []
        self._embeddings = []
        to_embed: list[tuple[int, str]] = []  # (index, content)

        for py_file in sorted(root.rglob("*.py")):
            rel = str(py_file.relative_to(root))
            source = py_file.read_text()
            mtime = py_file.stat().st_mtime

            # Invalidate stale cache entries
            self._cache.invalidate_path(rel, mtime)

            file_chunks = function_chunks(rel, source)
            for chunk in file_chunks:
                self._chunks.append(chunk)
                ch = _content_hash(chunk.content)
                cached = self._cache.get(ch)
                if cached is not None:
                    self._embeddings.append(np.array(cached))
                else:
                    idx = len(self._chunks) - 1
                    to_embed.append((idx, chunk.content))
                    self._embeddings.append(np.array([]))  # placeholder

        # Batch embed uncached chunks
        if to_embed:
            texts = [t for _, t in to_embed]
            vectors = self._embed_fn(texts)
            for (idx, content), vec in zip(to_embed, vectors):
                self._embeddings[idx] = np.array(vec)
                chunk = self._chunks[idx]
                py_file = root / chunk.path
                mtime = py_file.stat().st_mtime if py_file.exists() else 0.0
                self._cache.put(_content_hash(content), chunk.path, chunk.name, vec, mtime)

        return len(self._chunks)

    def query(self, task: str, top_k: int = 10) -> list[SearchResult]:
        """Find the most semantically similar chunks to a task description."""
        if not self._chunks:
            return []

        task_vec = np.array(self._embed_fn([task])[0])
        scores = [
            (i, _cosine_similarity(task_vec, emb))
            for i, emb in enumerate(self._embeddings)
            if emb.size > 0
        ]
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, sim in scores[:top_k]:
            chunk = self._chunks[i]
            results.append(
                SearchResult(
                    path=chunk.path,
                    chunk_name=chunk.name,
                    content=chunk.content,
                    similarity=sim,
                    start_line=chunk.start_line,
                )
            )
        return results

    def close(self) -> None:
        self._cache.close()
