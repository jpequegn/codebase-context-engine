"""Tests for the token budget packer."""

from ctx.packer import BudgetPacker, ContentType, ContextItem, assemble_prompt, count_tokens


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

def test_count_tokens_basic():
    assert count_tokens("hello world") > 0


def test_count_tokens_empty():
    assert count_tokens("") == 0


# ---------------------------------------------------------------------------
# BudgetPacker.pack
# ---------------------------------------------------------------------------

def test_pack_single_file_fits():
    packer = BudgetPacker(budget_tokens=1000)
    items = [{"path": "a.py", "content_type": "full", "content": "x = 1"}]
    result = packer.pack(items)
    assert len(result) == 1
    assert result[0].file == "a.py"
    assert result[0].content_type == ContentType.FULL


def test_pack_respects_budget():
    """Large file that exceeds budget is skipped."""
    packer = BudgetPacker(budget_tokens=5)
    big_content = "word " * 100  # way more than 5 tokens
    items = [{"path": "big.py", "content_type": "full", "content": big_content}]
    result = packer.pack(items)
    assert len(result) == 0


def test_pack_skips_oversized_includes_smaller():
    """A big item is skipped but a smaller one after it still gets included."""
    packer = BudgetPacker(budget_tokens=20)
    items = [
        {"path": "big.py", "content_type": "full", "content": "word " * 100},
        {"path": "small.py", "content_type": "full", "content": "x = 1"},
    ]
    result = packer.pack(items)
    assert len(result) == 1
    assert result[0].file == "small.py"


def test_pack_multiple_files():
    packer = BudgetPacker(budget_tokens=5000)
    items = [
        {"path": "a.py", "content_type": "full", "content": "def a(): pass"},
        {"path": "b.py", "content_type": "function", "content": "def b(): pass"},
        {"path": "c.py", "content_type": "signature", "content": "def c(): ..."},
    ]
    result = packer.pack(items)
    assert len(result) == 3
    assert result[0].content_type == ContentType.FULL
    assert result[1].content_type == ContentType.FUNCTION
    assert result[2].content_type == ContentType.SIGNATURE


def test_pack_uses_file_contents_fallback():
    """When item has no content key, file_contents dict is used."""
    packer = BudgetPacker(budget_tokens=1000)
    items = [{"path": "a.py", "content_type": "full"}]
    result = packer.pack(items, file_contents={"a.py": "print('hi')"})
    assert len(result) == 1
    assert result[0].content == "print('hi')"


def test_pack_skips_empty_content():
    packer = BudgetPacker(budget_tokens=1000)
    items = [{"path": "a.py", "content_type": "full", "content": ""}]
    result = packer.pack(items)
    assert len(result) == 0


def test_pack_empty_input():
    packer = BudgetPacker(budget_tokens=1000)
    assert packer.pack([]) == []


def test_total_tokens_within_budget():
    """Sum of token counts must not exceed the budget."""
    budget = 100
    packer = BudgetPacker(budget_tokens=budget)
    items = [
        {"path": f"f{i}.py", "content_type": "full", "content": f"var_{i} = {i}"}
        for i in range(50)
    ]
    result = packer.pack(items)
    total = sum(it.token_count for it in result)
    assert total <= budget


# ---------------------------------------------------------------------------
# assemble_prompt
# ---------------------------------------------------------------------------

def test_assemble_prompt_format():
    items = [
        ContextItem(file="a.py", content_type=ContentType.FULL, content="x = 1", token_count=3),
    ]
    prompt = assemble_prompt(items)
    assert "## a.py (full)" in prompt
    assert "x = 1" in prompt
    assert "```" in prompt


def test_assemble_prompt_multiple():
    items = [
        ContextItem(file="a.py", content_type=ContentType.FULL, content="x = 1", token_count=3),
        ContextItem(file="b.py", content_type=ContentType.FUNCTION, content="def f(): pass", token_count=5),
    ]
    prompt = assemble_prompt(items)
    assert "## a.py (full)" in prompt
    assert "## b.py (function)" in prompt


def test_assemble_prompt_empty():
    assert assemble_prompt([]) == ""


def test_assemble_prompt_tokens_within_budget():
    """End-to-end: pack then assemble, verify total ≤ budget."""
    budget = 200
    packer = BudgetPacker(budget_tokens=budget)
    items = [
        {"path": "main.py", "content_type": "full", "content": "def main():\n    print('hello')\n"},
        {"path": "utils.py", "content_type": "function", "content": "def helper(x):\n    return x + 1\n"},
        {"path": "config.py", "content_type": "full", "content": "DEBUG = True\nPORT = 8080\n"},
    ]
    packed = packer.pack(items)
    prompt = assemble_prompt(packed)
    assert count_tokens(prompt) <= budget + 100  # headers/fences add overhead
