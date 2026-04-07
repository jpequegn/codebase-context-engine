"""Tests for the token budget packer."""

import textwrap
from pathlib import Path

from ctx.budget import (
    BudgetPacker,
    ContentType,
    count_tokens,
    extract_function_source,
    extract_signatures,
)


def _write(tmp_path: Path, rel: str, content: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))


def test_count_tokens():
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0
    # Longer text should have more tokens
    assert count_tokens("a " * 100) > count_tokens("a " * 10)


def test_extract_function_source():
    source = textwrap.dedent("""\
        import os

        def foo(x):
            return x + 1

        def bar(y):
            return y * 2
    """)
    result = extract_function_source(source, "foo")
    assert result is not None
    assert "def foo(x):" in result
    assert "return x + 1" in result
    assert "def bar" not in result


def test_extract_class_source():
    source = textwrap.dedent("""\
        class MyClass:
            def method(self):
                pass

        def standalone():
            pass
    """)
    result = extract_function_source(source, "MyClass")
    assert result is not None
    assert "class MyClass:" in result
    assert "def method" in result
    assert "def standalone" not in result


def test_extract_signatures():
    source = textwrap.dedent("""\
        import os

        def foo(x: int) -> int:
            return x + 1

        class Bar:
            def method(self):
                pass

        async def baz(y):
            return y
    """)
    sigs = extract_signatures(source)
    assert "def foo(x: int) -> int: ..." in sigs
    assert "class Bar: ..." in sigs
    assert "def method(self): ..." in sigs
    assert "async def baz(y): ..." in sigs


def test_pack_respects_budget(tmp_path):
    # Create files with known content
    _write(tmp_path, "small.py", "x = 1")
    _write(tmp_path, "big.py", "y = 2\n" * 500)

    packer = BudgetPacker(budget_tokens=100)
    ranked = [("small.py", 0.9), ("big.py", 0.5)]
    items = packer.pack(ranked, str(tmp_path))

    # small.py should fit, big.py should be skipped (too many tokens)
    assert len(items) >= 1
    assert items[0].path == "small.py"
    assert packer.total_tokens(items) <= 100 or any(
        i.path in set() for i in items  # mentioned files can exceed
    )


def test_pack_mentioned_files_always_included(tmp_path):
    _write(tmp_path, "important.py", "x = 1\n" * 200)

    packer = BudgetPacker(budget_tokens=50)  # Very small budget
    ranked = [("important.py", 1.0)]
    items = packer.pack(ranked, str(tmp_path), mentioned_files={"important.py"})

    # Mentioned file is always included even if it exceeds budget
    assert len(items) == 1
    assert items[0].path == "important.py"
    assert items[0].content_type == ContentType.FULL


def test_pack_depth_map_signatures(tmp_path):
    _write(
        tmp_path,
        "deep.py",
        textwrap.dedent("""\
            def helper(x):
                return x + 1

            class Config:
                pass
        """),
    )

    packer = BudgetPacker(budget_tokens=8000)
    ranked = [("deep.py", 0.5)]
    items = packer.pack(ranked, str(tmp_path), depth_map={"deep.py": 2})

    assert len(items) == 1
    assert items[0].content_type == ContentType.SIGNATURE


def test_assemble_prompt(tmp_path):
    _write(tmp_path, "a.py", "x = 1")
    _write(tmp_path, "b.py", "y = 2")

    packer = BudgetPacker(budget_tokens=8000)
    ranked = [("a.py", 0.9), ("b.py", 0.5)]
    items = packer.pack(ranked, str(tmp_path))

    prompt = packer.assemble_prompt(items)
    assert "# Relevant Context" in prompt
    assert "## a.py" in prompt
    assert "## b.py" in prompt
    assert "```python" in prompt


def test_assemble_prompt_empty():
    packer = BudgetPacker()
    assert packer.assemble_prompt([]) == ""


def test_pack_skips_missing_files(tmp_path):
    packer = BudgetPacker(budget_tokens=8000)
    ranked = [("nonexistent.py", 0.9)]
    items = packer.pack(ranked, str(tmp_path))
    assert items == []


def test_total_tokens_matches_assembled(tmp_path):
    _write(tmp_path, "a.py", "x = 1")
    _write(tmp_path, "b.py", "y = 2")

    packer = BudgetPacker(budget_tokens=8000)
    ranked = [("a.py", 0.9), ("b.py", 0.5)]
    items = packer.pack(ranked, str(tmp_path))

    # Total tokens from items should approximately match the assembled prompt
    total = packer.total_tokens(items)
    prompt = packer.assemble_prompt(items)
    prompt_tokens = count_tokens(prompt)
    # They won't be exact because assemble_prompt adds a header and joins,
    # but should be in the same ballpark
    assert abs(total - prompt_tokens) < total * 0.5
