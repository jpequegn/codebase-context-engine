"""Tests for the Python AST parser."""

import textwrap
from pathlib import Path

from ctx.parsers.python import FileSymbols, parse_directory, parse_file


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))
    return p


def test_parse_file_imports(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(
        tmp_path,
        "pkg/app.py",
        """\
        import os
        import json
        from pkg.utils import helper
        from pathlib import Path
        """,
    )
    result = parse_file(str(tmp_path / "pkg/app.py"), str(tmp_path))
    assert "os" in result.imports
    assert "json" in result.imports
    assert "pkg.utils" in result.imports
    assert "pathlib" in result.imports
    assert result.local_imports == ["pkg.utils"]


def test_parse_file_defines(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(
        tmp_path,
        "pkg/models.py",
        """\
        class User:
            pass

        class Post:
            pass

        def create_user():
            pass

        async def fetch_posts():
            pass
        """,
    )
    result = parse_file(str(tmp_path / "pkg/models.py"), str(tmp_path))
    assert "User" in result.defines
    assert "Post" in result.defines
    assert "create_user" in result.defines
    assert "fetch_posts" in result.defines


def test_parse_file_calls(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(
        tmp_path,
        "pkg/service.py",
        """\
        import json

        class Service:
            def run(self):
                data = json.dumps({"a": 1})
                self.process(data)
                print(data)
        """,
    )
    result = parse_file(str(tmp_path / "pkg/service.py"), str(tmp_path))
    assert "json.dumps" in result.calls
    assert "process" in result.calls  # self.x() resolves to x
    assert "print" in result.calls


def test_parse_file_relative_import(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(
        tmp_path,
        "pkg/sub.py",
        """\
        from . import utils
        from .helpers import do_thing
        """,
    )
    result = parse_file(str(tmp_path / "pkg/sub.py"), str(tmp_path))
    # Relative imports are always local
    assert len(result.local_imports) == 2


def test_parse_directory(tmp_path):
    _write(tmp_path, "myapp/__init__.py", "")
    _write(
        tmp_path,
        "myapp/main.py",
        """\
        from myapp.db import connect

        def main():
            connect()
        """,
    )
    _write(
        tmp_path,
        "myapp/db.py",
        """\
        import sqlite3

        def connect():
            return sqlite3.connect(":memory:")
        """,
    )
    results = parse_directory(str(tmp_path))
    assert "myapp/main.py" in results
    assert "myapp/db.py" in results
    assert "myapp/__init__.py" in results
    assert "main" in results["myapp/main.py"].defines
    assert "connect" in results["myapp/db.py"].defines


def test_parse_directory_skips_syntax_errors(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/good.py", "def f(): pass")
    _write(tmp_path, "pkg/bad.py", "def ???")
    results = parse_directory(str(tmp_path))
    assert "pkg/good.py" in results
    assert "pkg/bad.py" not in results


def test_parse_file_on_self(tmp_path):
    """Parse our own parser module as a sanity check."""
    import ctx.parsers.python as mod

    parser_path = mod.__file__
    project_root = str(Path(parser_path).parent.parent.parent)
    result = parse_file(parser_path, project_root)
    assert "FileSymbols" in result.defines
    assert "parse_file" in result.defines
    assert "parse_directory" in result.defines
    assert "ast" in result.imports
