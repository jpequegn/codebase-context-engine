"""Self-eval: run eval tasks against this repository itself.

Validates that the eval framework works and provides baseline metrics.
Run with: uv run python evals/self_eval.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ctx.eval import EvalTask, evaluate_all, format_results_markdown

SELF_TASKS = [
    EvalTask(
        description="Add a new output format to the CLI assemble command",
        relevant_files=[
            "ctx/cli.py",
            "ctx/engine.py",
            "ctx/budget.py",
        ],
    ),
    EvalTask(
        description="Fix a bug in the Python parser import detection",
        relevant_files=[
            "ctx/parsers/python.py",
            "tests/test_parser.py",
        ],
    ),
    EvalTask(
        description="Add TypeScript support to the parser",
        relevant_files=[
            "ctx/parsers/python.py",
            "ctx/parsers/__init__.py",
        ],
    ),
    EvalTask(
        description="Improve the ranker scoring weights",
        relevant_files=[
            "ctx/ranker.py",
            "tests/test_ranker.py",
        ],
    ),
    EvalTask(
        description="Add a cache invalidation command to the CLI",
        relevant_files=[
            "ctx/cli.py",
            "ctx/embeddings.py",
        ],
    ),
    EvalTask(
        description="Fix the graph centrality calculation",
        relevant_files=[
            "ctx/graph.py",
            "tests/test_graph.py",
        ],
    ),
    EvalTask(
        description="Add git blame support to git history enrichment",
        relevant_files=[
            "ctx/git_history.py",
            "tests/test_git_history.py",
        ],
    ),
    EvalTask(
        description="Reduce token usage in the budget packer",
        relevant_files=[
            "ctx/budget.py",
            "tests/test_budget.py",
        ],
    ),
    EvalTask(
        description="Add batch embedding support to semantic search",
        relevant_files=[
            "ctx/embeddings.py",
            "tests/test_embeddings.py",
        ],
    ),
    EvalTask(
        description="Add a verbose flag to the engine assemble method",
        relevant_files=[
            "ctx/engine.py",
            "ctx/cli.py",
            "ctx/ranker.py",
        ],
    ),
]


if __name__ == "__main__":
    repo_path = str(Path(__file__).parent.parent)
    print(f"Running self-eval against: {repo_path}")
    print(f"Tasks: {len(SELF_TASKS)}\n")

    results = evaluate_all(repo_path, SELF_TASKS, use_semantic=False)
    report = format_results_markdown(results)
    print(report)

    # Write results
    output_path = Path(repo_path) / "EVAL_RESULTS.md"
    output_path.write_text(report)
    print(f"\nResults written to {output_path}")
