# Codebase Context Engine — Implementation Plan

## What We're Building

A context assembler for coding agents: given a task description, automatically retrieve and rank the most relevant code, documentation, and history to fit within a token budget.

This is the problem every AI coding tool (Cursor, GitHub Copilot, Unblocked, Amazon's Kiro) has to solve. The model is commodity. **Context assembly is the moat.**

## Why This Matters

Three separate podcasts this week (Software Engineering Daily × 2, Pragmatic Engineer) converged on the same insight: the bottleneck in AI-assisted development is not model quality — it's giving the agent the right context. "Just embed everything and RAG" produces mediocre results on code because code has structure (imports, call graphs, type signatures) that flat text search misses.

## Architecture

```
ctx/
├── __init__.py
├── engine.py         # ContextEngine: main assembly orchestrator
├── parsers/
│   ├── python.py     # AST-based symbol/import extraction
│   └── generic.py    # Line-based fallback for non-Python files
├── graph.py          # Call graph builder from AST data
├── git_history.py    # Recent commits + blame for touched files
├── ranker.py         # Score and rank context candidates
├── budget.py         # Token counter and context window packer
├── embeddings.py     # File/chunk embeddings for semantic search
└── cli.py            # `ctx assemble <task>` command

examples/
├── query_p3.py       # Run against parakeet-podcast-processor
└── query_self.py     # Run against this repo

tests/
├── test_parser.py
├── test_graph.py
└── test_budget.py

pyproject.toml
README.md
```

## Core Pipeline

```
Task description (natural language)
        ↓
1. SYMBOL EXTRACTION    — which files/symbols does the task mention?
        ↓
2. GRAPH EXPANSION      — what does each symbol import/call/reference?
        ↓
3. GIT ENRICHMENT       — recent commits + authors touching these files
        ↓
4. SEMANTIC SEARCH      — embed task, find semantically similar chunks
        ↓
5. RANKING              — score each candidate by relevance + recency + centrality
        ↓
6. BUDGET PACKING       — greedily fill token budget with highest-ranked items
        ↓
Assembled context (ready to inject into agent prompt)
```

## Implementation Phases

### Phase 1: Python AST parser (parsers/python.py)

Extract structured information from Python source files without executing them.

```python
@dataclass
class FileSymbols:
    path: str
    imports: list[str]         # modules imported
    defines: list[str]         # functions/classes defined
    calls: list[str]           # functions called
    dependencies: list[str]    # other project files imported
```

Use Python's `ast` module:
- `ast.Import` / `ast.ImportFrom` → imports
- `ast.FunctionDef` / `ast.ClassDef` → defines
- `ast.Call` → calls (resolve to local names where possible)

### Phase 2: Call graph builder (graph.py)

Build a directed graph: `file A calls function B defined in file C` → edge A→C.

```python
graph = CallGraph()
graph.build_from_directory("~/Code/parakeet-podcast-processor/p3/")

# Given an entry point, get all reachable files within N hops
relevant = graph.neighbors("p3/transcriber.py", depth=2)
# → ["p3/database.py", "p3/downloader.py", ...]
```

Use `networkx` for graph traversal. Store as adjacency list in memory (no persistence needed).

### Phase 3: Git history enrichment (git_history.py)

For a set of files, fetch:
- Last N commits that touched each file
- Commit message + author + date + diff summary
- `git blame` excerpt for recently changed lines

```python
history = GitHistory("~/Code/parakeet-podcast-processor")
recent = history.for_files(["p3/transcriber.py"], last_n_commits=5)
# → list of CommitSummary: hash, message, date, files_changed, diff_stat
```

Use `gitpython`. This adds crucial temporal context: "this file was refactored 2 days ago."

### Phase 4: Semantic search (embeddings.py)

Embed each file (or chunked file) and the task description. Retrieve by cosine similarity as a fallback for files the graph/parser missed.

- Chunk files at function boundaries (use AST to find function start/end lines)
- Embed with `text-embedding-3-small`
- Cache embeddings in SQLite (invalidate when file mtime changes)
- Return top-k most similar chunks

### Phase 5: Ranking (ranker.py)

Score each candidate context item on multiple signals:

```python
score = (
    0.35 * semantic_similarity     # embedding distance to task
  + 0.25 * graph_centrality        # how many other relevant files import this
  + 0.20 * recency_score           # recently modified files rank higher
  + 0.20 * mention_score           # task explicitly mentions this file/symbol
)
```

Return ranked list with scores and source signal.

### Phase 6: Token budget packer (budget.py)

Greedily pack highest-ranked items until token budget is exhausted.

Rules:
- Always include the file directly mentioned in the task (if any): full content
- For graph-expanded files: include only the relevant function/class, not whole file
- For semantic hits: include the matching chunk ± 10 lines context
- Budget default: 8000 tokens. Configurable via `--budget`.

Use `tiktoken` for accurate token counting.

### Phase 7: CLI

```bash
# Assemble context for a task
ctx assemble "add retry logic to the transcriber" --repo ~/Code/parakeet-podcast-processor

# Output to stdout (pipe to agent)
ctx assemble "fix the duplicate key error" --repo . --budget 6000 --format markdown

# Inspect what was assembled and why
ctx assemble "add a new CLI command" --verbose
# → shows each file, score, and which signal contributed

# Show call graph for a file
ctx graph p3/transcriber.py --depth 2

# Show top-k semantic matches for a query
ctx search "audio processing" --top-k 10
```

### Phase 8: Eval against P³

Run the context engine against 10 real tasks in the parakeet-podcast-processor codebase. For each task:
1. Assemble context
2. Ask Claude to complete the task using only the assembled context
3. Human-grade: did Claude have everything it needed? What was missing? What was noise?

Score: precision (relevant / total included) and recall (relevant included / total relevant).

## Key Design Decisions

**Why AST over embeddings-only?**
Embeddings find semantically similar text. Code relevance is often structural: "this file matters because it's imported by the target file." Combining both signals dramatically improves recall.

**Why not use tree-sitter?**
Python's `ast` module is sufficient for Python codebases and has zero dependencies. Tree-sitter would be needed for multi-language support — a follow-on.

**Why cache embeddings?**
Embedding a large codebase on every query is slow and expensive. File mtime-based cache invalidation is the right primitive: re-embed only changed files.

**What we're NOT building**
- Multi-language support (Python only for now)
- IDE plugin
- Real-time file watching
- Execution-based analysis (import and run the code)

## Acceptance Criteria

1. `ctx assemble` runs against P³ in <3 seconds for any task description
2. Assembled context fits within specified token budget (verified by tiktoken count)
3. For 8/10 eval tasks: human grades assembled context as "sufficient" (Claude could complete the task)
4. Verbose output shows which signal (graph/semantic/mention) contributed each file
5. Embedding cache makes second run 10x faster than first

## Learning Outcomes

After building this you will understand:
- Why "just RAG the repo" produces poor results on code
- How call graphs make context retrieval fundamentally different from document retrieval
- What token budget management looks like in practice (the constant tradeoff)
- The exact problem that Unblocked, Cursor, and Amazon Kiro are solving commercially
- Why codebase context assembly is the real moat in AI coding tools
