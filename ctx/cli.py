"""CLI: ctx assemble, ctx graph, ctx search with verbose mode."""

import json
import sys

import click

from ctx.budget import count_tokens
from ctx.embeddings import SemanticSearch
from ctx.engine import ContextEngine
from ctx.graph import CallGraph


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Codebase context engine: assemble relevant context for coding agents."""


@cli.command()
@click.argument("task")
@click.option("--repo", default=".", help="Path to the repository.")
@click.option("--budget", default=8000, help="Token budget for assembled context.")
@click.option(
    "--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]),
    help="Output format.",
)
@click.option("--verbose", is_flag=True, help="Show scoring details per file.")
@click.option(
    "--no-semantic", is_flag=True,
    help="Skip semantic search (no API key needed).",
)
def assemble(task, repo, budget, fmt, verbose, no_semantic):
    """Assemble context for a task description."""
    engine = ContextEngine(repo, budget_tokens=budget)
    try:
        items, ranked = engine.assemble(task, use_semantic=not no_semantic)
    finally:
        engine.close()

    if verbose:
        # Build a lookup from ranked items for score breakdown
        ranked_map = {r.path: r for r in ranked}
        click.echo(f"\n{'File':<45} {'Type':<12} {'Tokens':>7} {'Score':>6}  Signals", err=True)
        click.echo("-" * 100, err=True)
        for item in items:
            r = ranked_map.get(item.path)
            if r:
                signals = "  ".join(f"{k}={v:.2f}" for k, v in r.breakdown.items())
            else:
                signals = ""
            click.echo(
                f"{item.path:<45} {item.content_type.value:<12} {item.token_count:>7} {item.score:>6.3f}  {signals}",
                err=True,
            )
        total = engine.total_tokens(items)
        click.echo(f"\nTotal: {len(items)} files, {total} tokens (budget: {budget})", err=True)

    if fmt == "json":
        output = {
            "task": task,
            "items": [
                {
                    "path": item.path,
                    "content_type": item.content_type.value,
                    "token_count": item.token_count,
                    "score": item.score,
                }
                for item in items
            ],
            "total_tokens": engine.total_tokens(items),
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(engine.assemble_prompt(items))


@cli.command()
@click.argument("file")
@click.option("--repo", default=".", help="Path to the repository.")
@click.option("--depth", default=2, help="Graph traversal depth.")
def graph(file, repo, depth):
    """Show call graph for a file."""
    g = CallGraph()
    g.build(repo)

    deps = g.dependencies(file, depth=depth)
    dependents = g.dependents(file)

    click.echo(f"Dependencies of {file} (depth={depth}):")
    if deps:
        for d in deps:
            click.echo(f"  -> {d}")
    else:
        click.echo("  (none)")

    click.echo(f"\nDependents of {file}:")
    if dependents:
        for d in dependents:
            click.echo(f"  <- {d}")
    else:
        click.echo("  (none)")

    centrality = g.centrality()
    if file in centrality:
        click.echo(f"\nCentrality: {centrality[file]:.4f}")


@cli.command()
@click.argument("query")
@click.option("--repo", default=".", help="Path to the repository.")
@click.option("--top-k", default=10, help="Number of results.")
def search(query, repo, top_k):
    """Search for semantically similar code chunks."""
    from pathlib import Path

    cache_path = str(Path(repo) / ".ctx_cache.db")
    ss = SemanticSearch(cache_path=cache_path)
    try:
        count = ss.index(repo)
        click.echo(f"Indexed {count} chunks.", err=True)

        results = ss.query(query, top_k=top_k)
        for i, r in enumerate(results, 1):
            click.echo(f"\n--- {i}. {r.path}:{r.chunk_name} (similarity={r.similarity:.4f}) ---")
            click.echo(r.content)
    finally:
        ss.close()


@cli.command()
@click.option("--repo", default=".", help="Path to the repository.")
def index(repo):
    """Pre-build the embedding cache for a repository."""
    from pathlib import Path

    cache_path = str(Path(repo) / ".ctx_cache.db")
    ss = SemanticSearch(cache_path=cache_path)
    try:
        count = ss.index(repo)
        click.echo(f"Indexed {count} chunks from {repo}")
    finally:
        ss.close()
