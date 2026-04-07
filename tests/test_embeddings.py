"""Tests for semantic search with embeddings."""

import textwrap
from pathlib import Path

import numpy as np

from ctx.embeddings import (
    Chunk,
    EmbeddingCache,
    SemanticSearch,
    function_chunks,
)


def _write(tmp_path: Path, rel: str, content: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))


def _fake_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic fake embedder based on text hashing.

    Produces 32-dim vectors. Texts with shared words will have
    higher cosine similarity due to the bag-of-words approach.
    """
    vectors = []
    for text in texts:
        words = set(text.lower().split())
        vec = np.zeros(32)
        for word in words:
            idx = hash(word) % 32
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vectors.append(vec.tolist())
    return vectors


# --- function_chunks tests ---


def test_function_chunks_splits_functions():
    source = textwrap.dedent("""\
        import os

        def foo():
            return 1

        def bar():
            return 2

        class Baz:
            def method(self):
                pass
    """)
    chunks = function_chunks("test.py", source)
    names = [c.name for c in chunks]
    assert "foo" in names
    assert "bar" in names
    assert "Baz" in names
    assert "__module__" in names  # import os


def test_function_chunks_syntax_error():
    chunks = function_chunks("bad.py", "def ???")
    assert len(chunks) == 1
    assert chunks[0].name == "__module__"


def test_function_chunks_empty():
    chunks = function_chunks("empty.py", "")
    assert chunks == []


# --- EmbeddingCache tests ---


def test_cache_put_and_get(tmp_path):
    cache = EmbeddingCache(str(tmp_path / "test.db"))
    vec = [0.1, 0.2, 0.3]
    cache.put("hash1", "file.py", "func", vec, 1000.0)
    result = cache.get("hash1")
    assert result == vec
    cache.close()


def test_cache_miss(tmp_path):
    cache = EmbeddingCache(str(tmp_path / "test.db"))
    assert cache.get("nonexistent") is None
    cache.close()


def test_cache_invalidate(tmp_path):
    cache = EmbeddingCache(str(tmp_path / "test.db"))
    cache.put("hash1", "file.py", "func", [0.1], 1000.0)
    # Invalidate with new mtime
    cache.invalidate_path("file.py", 2000.0)
    assert cache.get("hash1") is None
    cache.close()


# --- SemanticSearch tests ---


def test_index_and_query(tmp_path):
    _write(
        tmp_path,
        "app/transcriber.py",
        """\
        def transcribe_audio(audio_file):
            \"\"\"Transcribe audio to text using speech recognition.\"\"\"
            return "transcribed text"

        def process_transcript(text):
            \"\"\"Process and clean transcript text.\"\"\"
            return text.strip()
        """,
    )
    _write(
        tmp_path,
        "app/database.py",
        """\
        def save_record(data):
            \"\"\"Save a record to the database.\"\"\"
            pass

        def query_records(filter):
            \"\"\"Query records from database.\"\"\"
            pass
        """,
    )

    cache_path = str(tmp_path / "cache.db")
    search = SemanticSearch(cache_path=cache_path, embed_fn=_fake_embed)
    count = search.index(str(tmp_path))
    assert count > 0

    results = search.query("audio transcription", top_k=5)
    assert len(results) > 0
    # The transcriber file should rank high for "audio transcription"
    paths = [r.path for r in results]
    assert "app/transcriber.py" in paths
    search.close()


def test_cache_speeds_up_reindex(tmp_path):
    _write(tmp_path, "mod.py", "def hello(): pass")

    cache_path = str(tmp_path / "cache.db")
    embed_count = 0

    def counting_embed(texts):
        nonlocal embed_count
        embed_count += len(texts)
        return _fake_embed(texts)

    # First index: should call embed
    search = SemanticSearch(cache_path=cache_path, embed_fn=counting_embed)
    search.index(str(tmp_path))
    first_count = embed_count
    assert first_count > 0
    search.close()

    # Second index: should use cache (no new embeds)
    embed_count = 0
    search = SemanticSearch(cache_path=cache_path, embed_fn=counting_embed)
    search.index(str(tmp_path))
    assert embed_count == 0  # All from cache
    search.close()


def test_query_empty_index(tmp_path):
    cache_path = str(tmp_path / "cache.db")
    search = SemanticSearch(cache_path=cache_path, embed_fn=_fake_embed)
    results = search.query("anything")
    assert results == []
    search.close()


def test_search_result_fields(tmp_path):
    _write(
        tmp_path,
        "example.py",
        """\
        def my_function():
            return 42
        """,
    )

    cache_path = str(tmp_path / "cache.db")
    search = SemanticSearch(cache_path=cache_path, embed_fn=_fake_embed)
    search.index(str(tmp_path))
    results = search.query("function", top_k=1)
    assert len(results) == 1
    r = results[0]
    assert r.path == "example.py"
    assert r.chunk_name == "my_function"
    assert r.start_line >= 1
    assert 0.0 <= r.similarity <= 1.0
    search.close()
