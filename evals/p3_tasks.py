"""P³ eval tasks: 10 real tasks against parakeet-podcast-processor.

Ground truth files are based on the P³ codebase structure:
    p3/
    ├── __init__.py
    ├── cli.py          # Click CLI with commands
    ├── config.py       # Configuration and defaults
    ├── database.py     # SQLite database operations
    ├── downloader.py   # Episode audio downloader
    ├── llm.py          # LLM client (Ollama/OpenAI)
    ├── rss.py          # RSS feed parser
    ├── server.py       # FastAPI server
    ├── summarizer.py   # Episode summarization
    └── transcriber.py  # Audio transcription

Run with: uv run python evals/p3_tasks.py ~/Code/parakeet-podcast-processor
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ctx.eval import EvalTask, evaluate_all, format_results_markdown

P3_TASKS = [
    EvalTask(
        description="Add retry logic to transcriber",
        relevant_files=[
            "p3/transcriber.py",
            "p3/config.py",
        ],
    ),
    EvalTask(
        description="Fix duplicate key error in episode insertion",
        relevant_files=[
            "p3/database.py",
            "p3/cli.py",
        ],
    ),
    EvalTask(
        description="Add a new p3 search CLI command",
        relevant_files=[
            "p3/cli.py",
            "p3/database.py",
        ],
    ),
    EvalTask(
        description="Export summaries to CSV format",
        relevant_files=[
            "p3/cli.py",
            "p3/database.py",
            "p3/summarizer.py",
        ],
    ),
    EvalTask(
        description="Add rate limiting to the Ollama client",
        relevant_files=[
            "p3/llm.py",
            "p3/config.py",
        ],
    ),
    EvalTask(
        description="Add authentication to the FastAPI server",
        relevant_files=[
            "p3/server.py",
            "p3/config.py",
        ],
    ),
    EvalTask(
        description="Change the default LLM model in config",
        relevant_files=[
            "p3/config.py",
            "p3/llm.py",
        ],
    ),
    EvalTask(
        description="Add a new RSS feed source",
        relevant_files=[
            "p3/rss.py",
            "p3/config.py",
            "p3/database.py",
        ],
    ),
    EvalTask(
        description="Debug why episodes stuck in downloaded status",
        relevant_files=[
            "p3/database.py",
            "p3/transcriber.py",
            "p3/cli.py",
        ],
    ),
    EvalTask(
        description="Add episode duration filter to p3 list-episodes",
        relevant_files=[
            "p3/cli.py",
            "p3/database.py",
        ],
    ),
]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python evals/p3_tasks.py <path-to-p3-repo>")
        print("Example: python evals/p3_tasks.py ~/Code/parakeet-podcast-processor")
        sys.exit(1)

    repo_path = sys.argv[1]
    print(f"Running eval against: {repo_path}")
    print(f"Tasks: {len(P3_TASKS)}\n")

    results = evaluate_all(repo_path, P3_TASKS, use_semantic=False)
    report = format_results_markdown(results)
    print(report)

    # Write results file
    output_path = Path(__file__).parent.parent / "EVAL_RESULTS.md"
    output_path.write_text(report)
    print(f"\nResults written to {output_path}")
