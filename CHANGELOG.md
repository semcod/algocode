# Changelog

All notable changes to `algocode` will be documented in this file.

## [0.1.0] - 2026-09-18

### Added
- Core algorithmic analysis engine:
  - Exact sliding-window SHA-256 code block duplicate detection.
  - Structural AST clone detection with identifier abstraction.
  - Workstream & path collision analysis across tickets and branches.
  - Algorithmic issue & backlog triage with git reconciliation and Jaccard duplicate clustering.
  - AST symbol, function, and import metric extraction.
- Tripartite `wellmanifest/nl-dsl-llm` standard adoption:
  - Layer 1: Polish & English deterministic natural language pattern matching.
  - Layer 2: Canonical DSL domain verbs (`code.dedup`, `conflict.check`, `issue.triage`, `code.inspect`, `repo.status`).
  - Layer 3: Adaptive LLM fallback compiler.
- Model Context Protocol (MCP) server over stdio with full JSON-RPC 2.0 interface.
- CLI interface supporting `--nl`, `--dsl`, subcommands, and `--self-test`.
- Conformance test suite with 14 unit tests covering all components.
