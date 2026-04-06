import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Codebase context engine: assemble relevant context for coding agents."""


@cli.command()
@click.argument("task")
@click.option("--repo", default=".", help="Path to the repository.")
@click.option("--budget", default=8000, help="Token budget for assembled context.")
@click.option("--format", "fmt", default="markdown", help="Output format.")
@click.option("--verbose", is_flag=True, help="Show scoring details.")
def assemble(task, repo, budget, fmt, verbose):
    """Assemble context for a task description."""
    click.echo(f"Assembling context for: {task}")
    click.echo(f"Repo: {repo}, Budget: {budget}, Format: {fmt}")


@cli.command()
@click.argument("file")
@click.option("--depth", default=2, help="Graph traversal depth.")
def graph(file, depth):
    """Show call graph for a file."""
    click.echo(f"Call graph for {file} (depth={depth})")


@cli.command()
@click.argument("query")
@click.option("--top-k", default=10, help="Number of results.")
def search(query, top_k):
    """Search for semantically similar code chunks."""
    click.echo(f"Searching for: {query} (top_k={top_k})")
