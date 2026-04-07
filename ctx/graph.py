"""Call graph builder: directed graph of file-level dependencies."""

from collections import deque

import networkx as nx

from ctx.parsers.python import parse_directory


class CallGraph:
    """Directed graph where edges represent file-level import dependencies."""

    def __init__(self):
        self._graph = nx.DiGraph()

    def build(self, directory: str) -> None:
        """Parse all .py files and build the dependency graph."""
        file_symbols = parse_directory(directory)

        # Map module paths to file relative paths for edge resolution.
        # e.g. "p3.database" -> "p3/database.py", "p3" -> "p3/__init__.py"
        module_to_file: dict[str, str] = {}
        for rel_path in file_symbols:
            # "p3/database.py" -> "p3.database"
            mod = rel_path.replace("/", ".").removesuffix(".py")
            if mod.endswith(".__init__"):
                mod = mod.removesuffix(".__init__")
            module_to_file[mod] = rel_path

        # Add all files as nodes
        for rel_path in file_symbols:
            self._graph.add_node(rel_path)

        # Add edges: file A imports module B -> edge from A to B's file
        for rel_path, symbols in file_symbols.items():
            for imp in symbols.local_imports:
                target = module_to_file.get(imp)
                if target and target != rel_path:
                    self._graph.add_edge(rel_path, target)

    def dependencies(self, file: str, depth: int = 1) -> list[str]:
        """Files that `file` depends on, via BFS up to `depth` hops."""
        if file not in self._graph:
            return []
        return self._bfs(file, depth, reverse=False)

    def dependents(self, file: str) -> list[str]:
        """Files that depend on `file` (reverse edges)."""
        if file not in self._graph:
            return []
        return list(self._graph.predecessors(file))

    def centrality(self) -> dict[str, float]:
        """Degree centrality for each file in the graph."""
        return nx.degree_centrality(self._graph)

    @property
    def files(self) -> list[str]:
        """All files in the graph."""
        return list(self._graph.nodes)

    def _bfs(self, start: str, depth: int, reverse: bool) -> list[str]:
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        visited.add(start)

        while queue:
            node, d = queue.popleft()
            if d >= depth:
                continue
            neighbors = self._graph.predecessors(node) if reverse else self._graph.successors(node)
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, d + 1))

        visited.discard(start)
        return sorted(visited)
