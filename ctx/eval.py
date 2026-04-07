"""Eval framework: measure precision and recall of context assembly."""

from __future__ import annotations

from dataclasses import dataclass

from ctx.engine import ContextEngine


@dataclass
class EvalTask:
    description: str
    relevant_files: list[str]  # ground truth: files needed for the task


@dataclass
class EvalResult:
    task: str
    included_files: list[str]
    relevant_files: list[str]
    relevant_included: list[str]
    relevant_missed: list[str]
    irrelevant_included: list[str]
    precision: float
    recall: float
    total_tokens: int


def evaluate_task(
    engine: ContextEngine,
    task: EvalTask,
    *,
    use_semantic: bool = False,
) -> EvalResult:
    """Run a single eval task and compute precision/recall."""
    items, _ = engine.assemble(task.description, use_semantic=use_semantic)

    included = {item.path for item in items}
    relevant = set(task.relevant_files)

    relevant_included = sorted(included & relevant)
    relevant_missed = sorted(relevant - included)
    irrelevant_included = sorted(included - relevant)

    precision = len(relevant_included) / len(included) if included else 0.0
    recall = len(relevant_included) / len(relevant) if relevant else 0.0

    return EvalResult(
        task=task.description,
        included_files=sorted(included),
        relevant_files=sorted(relevant),
        relevant_included=relevant_included,
        relevant_missed=relevant_missed,
        irrelevant_included=irrelevant_included,
        precision=precision,
        recall=recall,
        total_tokens=engine.total_tokens(items),
    )


def evaluate_all(
    repo_path: str,
    tasks: list[EvalTask],
    *,
    budget_tokens: int = 8000,
    use_semantic: bool = False,
) -> list[EvalResult]:
    """Run all eval tasks and return results."""
    engine = ContextEngine(repo_path, budget_tokens=budget_tokens)
    try:
        results = []
        for task in tasks:
            result = evaluate_task(engine, task, use_semantic=use_semantic)
            results.append(result)
        return results
    finally:
        engine.close()


def format_results_markdown(results: list[EvalResult]) -> str:
    """Format eval results as a markdown report."""
    lines = ["# Eval Results\n"]

    # Summary table
    lines.append("## Summary\n")
    lines.append("| # | Task | Precision | Recall | Tokens | Files |")
    lines.append("|---|------|-----------|--------|--------|-------|")

    total_precision = 0.0
    total_recall = 0.0

    for i, r in enumerate(results, 1):
        total_precision += r.precision
        total_recall += r.recall
        task_short = r.task[:50] + "..." if len(r.task) > 50 else r.task
        lines.append(
            f"| {i} | {task_short} | {r.precision:.2f} | {r.recall:.2f} "
            f"| {r.total_tokens} | {len(r.included_files)} |"
        )

    n = len(results)
    avg_p = total_precision / n if n else 0
    avg_r = total_recall / n if n else 0
    lines.append(f"| | **Average** | **{avg_p:.2f}** | **{avg_r:.2f}** | | |")

    # Acceptance criteria
    lines.append("\n## Acceptance Criteria\n")
    lines.append(f"- Precision >= 0.7: {'PASS' if avg_p >= 0.7 else 'FAIL'} ({avg_p:.2f})")
    lines.append(f"- Recall >= 0.6: {'PASS' if avg_r >= 0.6 else 'FAIL'} ({avg_r:.2f})")

    # Detail per task
    lines.append("\n## Detail\n")
    for i, r in enumerate(results, 1):
        lines.append(f"### Task {i}: {r.task}\n")
        lines.append(f"- **Precision**: {r.precision:.2f} ({len(r.relevant_included)}/{len(r.included_files)})")
        lines.append(f"- **Recall**: {r.recall:.2f} ({len(r.relevant_included)}/{len(r.relevant_files)})")
        lines.append(f"- **Tokens**: {r.total_tokens}")
        if r.relevant_included:
            lines.append(f"- **Relevant included**: {', '.join(r.relevant_included)}")
        if r.relevant_missed:
            lines.append(f"- **Relevant missed**: {', '.join(r.relevant_missed)}")
        if r.irrelevant_included:
            lines.append(f"- **Irrelevant included**: {', '.join(r.irrelevant_included)}")
        lines.append("")

    return "\n".join(lines)
