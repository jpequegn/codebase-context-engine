# Eval Results

> **Note**: This self-eval runs against the codebase-context-engine repo itself (22 files).
> Precision is low because all files fit within the 8000-token budget — the engine correctly
> includes all relevant files but also everything else. Precision becomes meaningful on larger
> codebases (like P³) where the budget forces selective inclusion.
>
> To run against P³: `uv run python evals/p3_tasks.py ~/Code/parakeet-podcast-processor`

## Summary

| # | Task | Precision | Recall | Tokens | Files |
|---|------|-----------|--------|--------|-------|
| 1 | Add a new output format to the CLI assemble comman... | 0.14 | 1.00 | 4587 | 22 |
| 2 | Fix a bug in the Python parser import detection | 0.09 | 1.00 | 4329 | 22 |
| 3 | Add TypeScript support to the parser | 0.09 | 1.00 | 3551 | 22 |
| 4 | Improve the ranker scoring weights | 0.09 | 1.00 | 4522 | 22 |
| 5 | Add a cache invalidation command to the CLI | 0.09 | 1.00 | 4587 | 22 |
| 6 | Fix the graph centrality calculation | 0.09 | 1.00 | 4082 | 22 |
| 7 | Add git blame support to git history enrichment | 0.09 | 1.00 | 3551 | 22 |
| 8 | Reduce token usage in the budget packer | 0.09 | 1.00 | 4712 | 22 |
| 9 | Add batch embedding support to semantic search | 0.09 | 1.00 | 3551 | 22 |
| 10 | Add a verbose flag to the engine assemble method | 0.14 | 1.00 | 4577 | 22 |
| | **Average** | **0.10** | **1.00** | | |

## Acceptance Criteria

- Precision >= 0.7: FAIL (0.10)
- Recall >= 0.6: PASS (1.00)

## Detail

### Task 1: Add a new output format to the CLI assemble command

- **Precision**: 0.14 (3/22)
- **Recall**: 1.00 (3/3)
- **Tokens**: 4587
- **Relevant included**: ctx/budget.py, ctx/cli.py, ctx/engine.py
- **Irrelevant included**: ctx/__init__.py, ctx/embeddings.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py

### Task 2: Fix a bug in the Python parser import detection

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 4329
- **Relevant included**: ctx/parsers/python.py, tests/test_parser.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/cli.py, ctx/embeddings.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_ranker.py

### Task 3: Add TypeScript support to the parser

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 3551
- **Relevant included**: ctx/parsers/__init__.py, ctx/parsers/python.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/cli.py, ctx/embeddings.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py

### Task 4: Improve the ranker scoring weights

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 4522
- **Relevant included**: ctx/ranker.py, tests/test_ranker.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/cli.py, ctx/embeddings.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py

### Task 5: Add a cache invalidation command to the CLI

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 4587
- **Relevant included**: ctx/cli.py, ctx/embeddings.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py

### Task 6: Fix the graph centrality calculation

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 4082
- **Relevant included**: ctx/graph.py, tests/test_graph.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/cli.py, ctx/embeddings.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/parsers/__init__.py, ctx/parsers/python.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_parser.py, tests/test_ranker.py

### Task 7: Add git blame support to git history enrichment

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 3551
- **Relevant included**: ctx/git_history.py, tests/test_git_history.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/cli.py, ctx/embeddings.py, ctx/engine.py, ctx/eval.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py

### Task 8: Reduce token usage in the budget packer

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 4712
- **Relevant included**: ctx/budget.py, tests/test_budget.py
- **Irrelevant included**: ctx/__init__.py, ctx/cli.py, ctx/embeddings.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py

### Task 9: Add batch embedding support to semantic search

- **Precision**: 0.09 (2/22)
- **Recall**: 1.00 (2/2)
- **Tokens**: 3551
- **Relevant included**: ctx/embeddings.py, tests/test_embeddings.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/cli.py, ctx/engine.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, ctx/ranker.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py

### Task 10: Add a verbose flag to the engine assemble method

- **Precision**: 0.14 (3/22)
- **Recall**: 1.00 (3/3)
- **Tokens**: 4577
- **Relevant included**: ctx/cli.py, ctx/engine.py, ctx/ranker.py
- **Irrelevant included**: ctx/__init__.py, ctx/budget.py, ctx/embeddings.py, ctx/eval.py, ctx/git_history.py, ctx/graph.py, ctx/parsers/__init__.py, ctx/parsers/python.py, evals/p3_tasks.py, evals/self_eval.py, tests/__init__.py, tests/test_budget.py, tests/test_cli.py, tests/test_embeddings.py, tests/test_eval.py, tests/test_git_history.py, tests/test_graph.py, tests/test_parser.py, tests/test_ranker.py
