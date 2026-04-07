"""Token budget packer: greedily fill a context window from ranked items."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import tiktoken


class ContentType(str, Enum):
    """How much of a file is included."""

    FULL = "full"
    FUNCTION = "function"
    SIGNATURE = "signature"
    CHUNK = "chunk"


@dataclass
class ContextItem:
    """A single piece of context selected for the prompt."""

    file: str
    content_type: ContentType
    content: str
    token_count: int


_encoder = tiktoken.encoding_for_model("gpt-4")


def count_tokens(text: str) -> int:
    """Return the number of tokens in *text* using the gpt-4 tokenizer."""
    return len(_encoder.encode(text))


class BudgetPacker:
    """Pack ranked items into a token budget.

    Priority order (from issue #3):
      1. Files explicitly named in task → full content
      2. Direct graph neighbours (depth 1) → relevant function / class
      3. Deeper graph neighbours (depth 2) → signatures only
      4. Semantic hits → matching chunk ± context
      5. Stop when budget exhausted
    """

    def __init__(self, budget_tokens: int = 8000) -> None:
        self.budget_tokens = budget_tokens

    def pack(
        self,
        ranked_items: list[dict],
        *,
        file_contents: dict[str, str] | None = None,
    ) -> list[ContextItem]:
        """Select items that fit within the token budget.

        Parameters
        ----------
        ranked_items:
            Dicts with at least ``path`` and ``content_type`` keys.
            ``content_type`` is one of the :class:`ContentType` values.
            ``content`` is the text to include (pre-extracted by the caller).
        file_contents:
            Optional mapping of path → full file text.  When a ranked item
            has ``content_type="full"`` but no ``content`` key, the packer
            looks it up here.

        Returns a list of :class:`ContextItem` that fit within the budget.
        """
        file_contents = file_contents or {}
        result: list[ContextItem] = []
        used = 0

        for item in ranked_items:
            path = item["path"]
            ctype = ContentType(item.get("content_type", ContentType.FULL))
            content = item.get("content") or file_contents.get(path, "")
            if not content:
                continue

            tokens = count_tokens(content)
            if used + tokens > self.budget_tokens:
                # Try to fit remaining items — a smaller one may still fit.
                continue

            result.append(
                ContextItem(
                    file=path,
                    content_type=ctype,
                    content=content,
                    token_count=tokens,
                )
            )
            used += tokens

        return result


def assemble_prompt(items: list[ContextItem]) -> str:
    """Format context items as a markdown string with file-path headers."""
    if not items:
        return ""

    sections: list[str] = []
    for item in items:
        header = f"## {item.file} ({item.content_type.value})"
        sections.append(f"{header}\n\n```\n{item.content}\n```")

    return "\n\n".join(sections) + "\n"
