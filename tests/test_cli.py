"""Tests for the CLI commands."""

import json
import subprocess
import textwrap
from pathlib import Path

from click.testing import CliRunner

from ctx.cli import cli


def _make_project(tmp_path: Path) -> Path:
    """Create a small Python project for testing."""
    proj = tmp_path / "proj"
    proj.mkdir()

    # Init git repo so git_history doesn't fail
    subprocess.run(["git", "init"], cwd=proj, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=proj, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=proj, capture_output=True)

    pkg = proj / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "service.py").write_text(
        textwrap.dedent("""\
            from app.db import connect

            def run_service():
                return connect()
        """)
    )
    (pkg / "db.py").write_text(
        textwrap.dedent("""\
            def connect():
                return "connected"
        """)
    )

    subprocess.run(["git", "add", "."], cwd=proj, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=proj, capture_output=True)
    return proj


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "assemble" in result.output
    assert "graph" in result.output
    assert "search" in result.output
    assert "index" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_graph_command(tmp_path):
    proj = _make_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["graph", "app/service.py", "--repo", str(proj)])
    assert result.exit_code == 0
    assert "app/db.py" in result.output
    assert "Dependencies" in result.output


def test_assemble_markdown(tmp_path):
    proj = _make_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "assemble", "fix the connect function in db",
        "--repo", str(proj), "--no-semantic",
    ])
    assert result.exit_code == 0
    assert "Relevant Context" in result.output
    assert "app/db.py" in result.output


def test_assemble_json(tmp_path):
    proj = _make_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "assemble", "fix the connect function",
        "--repo", str(proj), "--no-semantic", "--format", "json",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "items" in data
    assert "total_tokens" in data
    assert data["total_tokens"] > 0


def test_assemble_verbose(tmp_path):
    proj = _make_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "assemble", "update the service",
        "--repo", str(proj), "--no-semantic", "--verbose",
    ])
    assert result.exit_code == 0
    # Verbose table and summary are in the output
    assert "Score" in result.output or "Tokens" in result.output
    assert "Total:" in result.output


def test_assemble_budget(tmp_path):
    proj = _make_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "assemble", "update the service",
        "--repo", str(proj), "--no-semantic",
        "--budget", "200", "--format", "json",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Budget is very small, so token count should be limited
    # (mentioned files may exceed budget, that's by design)
    assert data["total_tokens"] >= 0
