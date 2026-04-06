"""Python AST parser: extract symbols, imports, and calls from .py files."""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileSymbols:
    path: str
    imports: list[str] = field(default_factory=list)
    local_imports: list[str] = field(default_factory=list)
    defines: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)


class _SymbolVisitor(ast.NodeVisitor):
    """AST visitor that collects imports, definitions, and calls."""

    def __init__(self, project_packages: set[str]):
        self.imports: list[str] = []
        self.local_imports: list[str] = []
        self.defines: list[str] = []
        self.calls: list[str] = []
        self._project_packages = project_packages

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
            if self._is_local(alias.name):
                self.local_imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if node.level > 0:
            # Relative import — always local
            self.imports.append(module)
            self.local_imports.append(module)
        else:
            self.imports.append(module)
            if self._is_local(module):
                self.local_imports.append(module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.defines.append(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.defines.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self._resolve_call_name(node.func)
        if name:
            self.calls.append(name)
        self.generic_visit(node)

    def _resolve_call_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = self._resolve_call_name(node.value)
            if value == "self":
                return node.attr
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        return None

    def _is_local(self, module: str) -> bool:
        top_level = module.split(".")[0]
        return top_level in self._project_packages


def _find_project_packages(project_root: str) -> set[str]:
    """Find top-level Python packages in the project root."""
    packages = set()
    root = Path(project_root)
    for entry in root.iterdir():
        if entry.is_dir() and (entry / "__init__.py").exists():
            packages.add(entry.name)
        elif entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
            packages.add(entry.stem)
    return packages


def parse_file(path: str, project_root: str) -> FileSymbols:
    """Parse a Python file and extract symbols, imports, and calls."""
    source = Path(path).read_text()
    tree = ast.parse(source, filename=path)

    project_packages = _find_project_packages(project_root)
    visitor = _SymbolVisitor(project_packages)
    visitor.visit(tree)

    return FileSymbols(
        path=os.path.relpath(path, project_root),
        imports=visitor.imports,
        local_imports=visitor.local_imports,
        defines=visitor.defines,
        calls=visitor.calls,
    )


def parse_directory(root: str) -> dict[str, FileSymbols]:
    """Parse all .py files in a directory tree."""
    results = {}
    root_path = Path(root)
    for py_file in sorted(root_path.rglob("*.py")):
        rel = str(py_file.relative_to(root_path))
        try:
            results[rel] = parse_file(str(py_file), root)
        except SyntaxError:
            continue
    return results
