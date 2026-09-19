---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "code-analysis",
  "kind": "information",
  "version": 1,
  "title": "Deterministic code analysis and clone detection in algocode",
  "status": "accepted",
  "owner": "semcod/algocode",
  "created": "2026-09-19",
  "updated": "2026-09-19",
  "review_after": "2026-10-19",
  "source_revision": "9677719b080227cad2a5e7cb5873b7324a57a78e",
  "affected_repositories": [
    "semcod/algocode"
  ],
  "evidence": [
    "https://github.com/semcod/algocode/commit/9677719b080227cad2a5e7cb5873b7324a57a78e"
  ]
}
---

# Deterministic code analysis and clone detection

<!-- docs:section purpose -->
## Purpose

Document the deterministic code analysis architecture, AST inspection protocols,
and polyglot clone detection engines provided by `semcod/algocode`.

<!-- docs:section scope -->
## Scope

Covers `CodeAnalysisEngine` capabilities including polyglot structural clone
detection (Python, TypeScript, JavaScript, Go, Rust, PHP), AST tokenization,
bracket and brace balance tracking, and top-level convenience API functions.

<!-- docs:section content -->
## Content

### 1. Architectural principles

- **Deterministic by Default**: Perform static parsing, AST symbol extraction,
  and normalized structural matching before falling back to heuristics.
- **Polyglot Parsing**: Provide specialized AST normalization for C-family
  languages (TypeScript, JavaScript, Go, Rust, PHP) via balanced block extraction
  and Python via standard `ast` parsing.
- **Model Context Protocol (MCP)**: Expose deterministic analysis tools over
  standard stdio transport for agent orchestration.

### 2. Convenience API

The module exposes convenient top-level functions:
- `scan_duplicates(target_path, min_lines=5, extensions=None, max_files=200)`
- `inspect_ast(code, language='python')`
- `check_conflict(incoming_diff, baseline_code)`
- `check_conflicts(tasks)`
- `triage_issues(issues)`

### 3. Clone detection normalization (Type-1 & Type-2)

Clone detection implements sliding-window hashing across statement sequences.
Type-1 clones detect exact token equivalence; Type-2 clones normalize identifier
names and literals to identify structurally identical code blocks.

<!-- docs:section limitations -->
## Limitations

Structural AST analysis depends on syntactically valid code blocks. Truncated
or malformed files fallback to line-level hash comparisons.

<!-- docs:section next_actions -->
## Next actions

Integrate semantic drift detection for documentation API references and maintain
benchmark test suites for polyglot block extraction.

<!-- docs:section evidence -->
## Evidence

Verified by unit test suite in `tests/test_engine.py` (17/17 tests passing)
and live packaging verification.
