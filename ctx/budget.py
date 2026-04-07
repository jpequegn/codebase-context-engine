"""Token budget packer: greedily fill a context window with ranked items."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import tiktoken


class ContentType(str, Enum):
    FULL = "full"
    FUNCTION = "function"
    SIGNATURE = "signature"
    CHUNK = "chunk"


@dataclass
class ContextItem:
    path: str
    content_type: ContentType
    content: str
    token_count: int
    score: float = 0.0


_encoder = tiktoken.encoding_for_model("gpt-4")


def count_tokens(text: str) -> int:
    """Count tokens using the GPT-4 tokenizer."""
    return len(_encoder.encode(text))


def read_file_content(path: str, project_root: str) -> str | None:
    """Read file content, returning None if the file doesn't exist."""
    full_path = Path(project_root) / path
    if not full_path.is_file():
        return None
    return full_path.read_text()


def extract_function_source(source: str, name: str) -> str | None:
    """Extract a function or class definition from source by name.

    Uses a simple indentation-based approach: finds the def/class line
    and includes all following lines that are indented deeper or blank.
    """
    lines = source.split("\n")
    start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"def {name}(") or stripped.startswith(
            f"def {name} ("
        ):
            start = i
            break
        if stripped.startswith(f"class {name}(") or stripped.startswith(
            f"class {name}:"
        ):
            start = i
            break

    if start is None:
        return None

    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() == "":
            end += 1
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent:
            break
        end += 1

    return "\n".join(lines[start:end])


def extract_signatures(source: str) -> str:
    """Extract function and class signatures (first line only) from source."""
    sigs = []
    for line in source.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            # Remove the trailing colon and body, keep the full signature
            sig = stripped.rstrip()
            if sig.endswith(":"):
                sig = sig[:-1]
            sigs.append(sig + ": ...")
        elif stripped.startswith("class "):
            sig = stripped.rstrip()
            if sig.endswith(":"):
                sig = sig[:-1]
            sigs.append(sig + ": ...")
    return "\n".join(sigs)


def extract_chunk(source: str, match_line: int, context_lines: int = 10) -> str:
    """Extract a chunk around a matching line with context."""
    lines = source.split("\n")
    start = max(0, match_line - context_lines)
    end = min(len(lines), match_line + context_lines + 1)
    return "\n".join(lines[start:end])


class BudgetPacker:
    """Greedily pack ranked context items into a token budget."""

    def __init__(self, budget_tokens: int = 8000):
        self.budget_tokens = budget_tokens

    def pack(
        self,
        ranked_paths: list[tuple[str, float]],
        project_root: str,
        *,
        mentioned_files: set[str] | None = None,
        depth_map: dict[str, int] | None = None,
    ) -> list[ContextItem]:
        """Pack context items into the budget.

        Parameters
        ----------
        ranked_paths:
            List of (file_path, score) tuples, sorted by descending score.
        project_root:
            Root directory of the project.
        mentioned_files:
            Files explicitly mentioned in the task — always included in full.
        depth_map:
            Graph distance from mentioned files. depth=1 gets functions,
            depth>=2 gets signatures only.
        """
        mentioned = mentioned_files or set()
        depths = depth_map or {}
        items: list[ContextItem] = []
        tokens_used = 0

        for path, score in ranked_paths:
            source = read_file_content(path, project_root)
            if source is None:
                continue

            if path in mentioned:
                content_type = ContentType.FULL
                content = source
            elif depths.get(path, 0) <= 1:
                content_type = ContentType.FUNCTION
                # For depth-1 neighbors, include relevant functions;
                # fall back to signatures if we can't isolate functions.
                sigs = extract_signatures(source)
                if sigs:
                    content = sigs
                    content_type = ContentType.SIGNATURE
                else:
                    content = source
                    content_type = ContentType.FULL
            else:
                content_type = ContentType.SIGNATURE
                content = extract_signatures(source)
                if not content:
                    continue

            formatted = f"## {path}\n\n```python\n{content}\n```\n"
            token_count = count_tokens(formatted)

            # Mentioned files always go in regardless of budget
            if path not in mentioned and tokens_used + token_count > self.budget_tokens:
                continue

            items.append(
                ContextItem(
                    path=path,
                    content_type=content_type,
                    content=formatted,
                    token_count=token_count,
                    score=score,
                )
            )
            tokens_used += token_count

        return items

    def assemble_prompt(self, items: list[ContextItem]) -> str:
        """Format context items as a markdown prompt."""
        if not items:
            return ""

        parts = ["# Relevant Context\n"]
        for item in items:
            parts.append(item.content)
        return "\n".join(parts)

    def total_tokens(self, items: list[ContextItem]) -> int:
        """Total token count across all items."""
        return sum(item.token_count for item in items)
