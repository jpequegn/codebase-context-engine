"""Tests for the call graph builder."""

import textwrap
from pathlib import Path

from ctx.graph import CallGraph


def _write(tmp_path: Path, rel: str, content: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))


def _make_project(tmp_path):
    """Create a small project with known dependency structure.

    Structure:
        app/
        ├── __init__.py
        ├── cli.py        → imports app.service, app.config
        ├── service.py    → imports app.database, app.config
        ├── database.py   → imports app.config
        └── config.py     → no local imports
    """
    _write(tmp_path, "app/__init__.py", "")
    _write(tmp_path, "app/config.py", "DB_URL = 'sqlite:///test.db'")
    _write(
        tmp_path,
        "app/database.py",
        """\
        from app.config import DB_URL

        def connect():
            return DB_URL
        """,
    )
    _write(
        tmp_path,
        "app/service.py",
        """\
        from app.database import connect
        from app.config import DB_URL

        def run():
            connect()
        """,
    )
    _write(
        tmp_path,
        "app/cli.py",
        """\
        from app.service import run
        from app.config import DB_URL

        def main():
            run()
        """,
    )


def test_build_and_dependencies(tmp_path):
    _make_project(tmp_path)
    g = CallGraph()
    g.build(str(tmp_path))

    deps = g.dependencies("app/cli.py", depth=1)
    assert "app/service.py" in deps
    assert "app/config.py" in deps


def test_dependencies_depth_2(tmp_path):
    _make_project(tmp_path)
    g = CallGraph()
    g.build(str(tmp_path))

    deps = g.dependencies("app/cli.py", depth=2)
    # depth 2: cli -> service -> database, cli -> config (already at depth 1)
    assert "app/service.py" in deps
    assert "app/config.py" in deps
    assert "app/database.py" in deps


def test_dependents(tmp_path):
    _make_project(tmp_path)
    g = CallGraph()
    g.build(str(tmp_path))

    # config.py is imported by cli, service, database
    deps = g.dependents("app/config.py")
    assert "app/cli.py" in deps
    assert "app/service.py" in deps
    assert "app/database.py" in deps


def test_centrality(tmp_path):
    _make_project(tmp_path)
    g = CallGraph()
    g.build(str(tmp_path))

    cent = g.centrality()
    # config.py should have highest centrality (most connections)
    assert cent["app/config.py"] == max(cent.values())


def test_unknown_file(tmp_path):
    _make_project(tmp_path)
    g = CallGraph()
    g.build(str(tmp_path))

    assert g.dependencies("nonexistent.py") == []
    assert g.dependents("nonexistent.py") == []


def test_files_property(tmp_path):
    _make_project(tmp_path)
    g = CallGraph()
    g.build(str(tmp_path))

    assert len(g.files) == 5  # __init__, config, database, service, cli
