"""Tests for the eval framework."""

import subprocess
import textwrap
from pathlib import Path

from ctx.eval import EvalTask, evaluate_all, evaluate_task, format_results_markdown
from ctx.engine import ContextEngine


def _make_project(tmp_path: Path) -> Path:
    """Create a small project for eval testing."""
    proj = tmp_path / "proj"
    proj.mkdir()

    subprocess.run(["git", "init"], cwd=proj, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=proj, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=proj, capture_output=True)

    pkg = proj / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "cli.py").write_text(
        textwrap.dedent("""\
            from app.service import run

            def main():
                run()
        """)
    )
    (pkg / "service.py").write_text(
        textwrap.dedent("""\
            from app.db import connect

            def run():
                return connect()
        """)
    )
    (pkg / "db.py").write_text(
        textwrap.dedent("""\
            def connect():
                return "connected"

            def query(sql):
                return []
        """)
    )

    subprocess.run(["git", "add", "."], cwd=proj, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=proj, capture_output=True)
    return proj


def test_evaluate_task_precision_recall(tmp_path):
    proj = _make_project(tmp_path)
    engine = ContextEngine(str(proj), budget_tokens=8000)

    task = EvalTask(
        description="Fix the connect function in db",
        relevant_files=["app/db.py", "app/service.py"],
    )
    result = evaluate_task(engine, task, use_semantic=False)
    engine.close()

    # db.py should be included (mentioned in task)
    assert "app/db.py" in result.included_files
    assert result.precision >= 0.0
    assert result.recall >= 0.0
    assert result.precision <= 1.0
    assert result.recall <= 1.0
    assert result.total_tokens > 0


def test_evaluate_all(tmp_path):
    proj = _make_project(tmp_path)
    tasks = [
        EvalTask(
            description="Update the CLI main function",
            relevant_files=["app/cli.py"],
        ),
        EvalTask(
            description="Fix the database query function",
            relevant_files=["app/db.py"],
        ),
    ]
    results = evaluate_all(str(proj), tasks, use_semantic=False)
    assert len(results) == 2
    assert all(r.total_tokens > 0 for r in results)


def test_format_results_markdown(tmp_path):
    proj = _make_project(tmp_path)
    tasks = [
        EvalTask(
            description="Fix the database",
            relevant_files=["app/db.py"],
        ),
    ]
    results = evaluate_all(str(proj), tasks, use_semantic=False)
    report = format_results_markdown(results)

    assert "# Eval Results" in report
    assert "Summary" in report
    assert "Precision" in report
    assert "Recall" in report
    assert "PASS" in report or "FAIL" in report


def test_perfect_recall_when_file_mentioned(tmp_path):
    proj = _make_project(tmp_path)
    engine = ContextEngine(str(proj), budget_tokens=8000)

    # Task mentions "cli" — app/cli.py should be included
    task = EvalTask(
        description="Update the cli command",
        relevant_files=["app/cli.py"],
    )
    result = evaluate_task(engine, task, use_semantic=False)
    engine.close()

    assert "app/cli.py" in result.relevant_included
    assert result.recall == 1.0
